import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from agents.code_rewriter_agent import CodeRewriterAgent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT_ROOT / "data" / "test_cases" / "python"
ORIGINAL = 'password = "fixture-placeholder"\n'
REPLACEMENT = 'import os\npassword = os.environ["EXAMPLE_PASSWORD"]'
SECURITY_FINDING = {
    "finding_type": "hardcoded_secret",
    "severity": "critical",
    "line_number": 1,
    "code_snippet": ORIGINAL.strip(),
    "description": "A password is stored in the source",
}


def completion_client(content, finish_reason="stop"):
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content), finish_reason=finish_reason
            )
        ]
    )
    client = Mock()
    client.chat.completions.create.return_value = response
    return client


def model_response(code):
    return f"REWRITTEN_CODE:\n{code}\n\nEXPLANATION:\nExample proposal."


class RewriteTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            self.agent = CodeRewriterAgent()

    def rewrite(self, content, original=ORIGINAL, language="python", finish_reason="stop"):
        self.agent.client = completion_client(content, finish_reason)
        result = self.agent.execute(
            {
                "code": original,
                "language": language,
                "security_findings": [SECURITY_FINDING],
            }
        )
        self.agent.client.chat.completions.create.assert_called_once()
        return result["rewrites"]

    def test_valid_python_proposal_is_full_source_and_manual_review(self):
        proposals = self.rewrite(model_response(f"```python\n{REPLACEMENT}\n```"))
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal["original_code"], ORIGINAL)
        self.assertEqual(proposal["rewritten_code"], REPLACEMENT)
        self.assertEqual(proposal["proposal_kind"], "full_source")
        self.assertEqual(proposal["validation_status"], "syntax_checked")
        self.assertEqual(proposal["rewrite_mode"], "review")
        self.assertIsNone(proposal["confidence_score"])

    def test_missing_malformed_and_empty_completions_return_no_proposal(self):
        for response in (None, "Consider reading this value from the environment.", model_response("")):
            with self.subTest(response=response):
                self.assertEqual(self.rewrite(response), [])

    def test_truncated_completion_is_rejected_even_when_text_compiles(self):
        self.assertEqual(self.rewrite(model_response(REPLACEMENT), finish_reason="length"), [])

    def test_exact_and_formatting_only_replacements_return_no_proposal(self):
        for source in (ORIGINAL, "# Updated\npassword='fixture-placeholder'"):
            with self.subTest(source=source):
                self.assertEqual(self.rewrite(model_response(source)), [])

    def test_invalid_python_and_invalid_module_scope_return_no_proposal(self):
        for source in ("def broken(:", "return 0"):
            with self.subTest(source=source):
                self.assertEqual(self.rewrite(model_response(source)), [])

    def test_behavior_changing_proposal_is_never_executed_or_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "executed"
            source = f"from pathlib import Path\nPath({str(marker)!r}).touch()"
            proposals = self.rewrite(model_response(source))
            self.assertFalse(marker.exists())
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["validation_status"], "syntax_checked")
        self.assertEqual(proposals[0]["rewrite_mode"], "review")
        self.assertIsNone(proposals[0]["confidence_score"])

    def test_non_python_is_explicitly_unchecked(self):
        proposals = self.rewrite(
            model_response("SELECT id FROM users;"),
            original="SELECT * FROM users;",
            language="sql",
        )
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["validation_status"], "unchecked")
        self.assertEqual(proposals[0]["proposal_kind"], "full_source")
        self.assertEqual(proposals[0]["rewrite_mode"], "review")
        self.assertIsNone(proposals[0]["confidence_score"])


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to disposable PostgreSQL")
class ReviewApiTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"OPENAI_API_KEY": ""}))
        from api import server
        from db import db

        schema = f"p07_test_{uuid4().hex}"
        url = os.environ["TEST_DATABASE_URL"]
        admin = create_engine(url)
        self.addCleanup(admin.dispose)
        with admin.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        self.addCleanup(self.drop_schema, admin, schema)

        engine = create_engine(url, connect_args={"options": f"-c search_path={schema}"})
        self.addCleanup(engine.dispose)
        self.sessions = sessionmaker(bind=engine)
        self.enterContext(patch.object(db, "engine", engine))
        self.enterContext(patch.object(db, "SessionLocal", self.sessions))
        self.client = self.enterContext(TestClient(server.app))
        self.server = server
        self.db = db

    @staticmethod
    def drop_schema(engine, schema):
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))

    def post_review(self, code):
        response = self.client.post("/review", json={"code": code, "language": "python"})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_static_fixtures_and_persisted_summaries(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        sources = {
            "insecure": (FIXTURES / "insecure" / "sql_injection.py").read_text(),
            "secure": (FIXTURES / "secure" / "sql_safe.py").read_text(),
        }
        for label, code in sources.items():
            with self.subTest(label=label):
                result = self.post_review(code)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["rewrites"], [])
                types = {finding["finding_type"] for finding in result["security"]["findings"]}
                self.assertEqual("sql_injection" in types, label == "insecure")
                with self.sessions() as session:
                    saved = session.scalar(
                        select(self.db.CodeReview).where(
                            self.db.CodeReview.review_id == result["review_id"]
                        )
                    )
                    self.assertIsNotNone(saved)
                    self.assertEqual(saved.code_content, code)
                    self.assertEqual(saved.status, "completed")
                    self.assertEqual(
                        saved.review_summary.total_findings,
                        result["summary"]["total_findings"],
                    )

    def test_review_api_preserves_manual_proposal_status(self):
        client = completion_client(model_response(REPLACEMENT))
        with patch.object(self.server.orchestrator.rewriter_agent, "client", client):
            result = self.post_review(ORIGINAL)
        self.assertEqual(len(result["rewrites"]), 1)
        proposal = result["rewrites"][0]
        self.assertEqual(proposal["rewrite_mode"], "review")
        self.assertEqual(proposal["validation_status"], "syntax_checked")
        self.assertIsNone(proposal["confidence_score"])
