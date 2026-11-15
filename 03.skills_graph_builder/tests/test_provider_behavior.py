"""Offline regressions for the Skills Graph Builder API."""

import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from textwrap import dedent
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import httpx
import numpy as np
from openai import APITimeoutError, OpenAI, RateLimitError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def local_environment(tracking_dir):
    return {
        "OPENAI_API_KEY": "offline-test-key",
        "ROLE_CATALOG_CSV": str(PROJECT_ROOT / "data/roles/role_skill_requirements.csv"),
        "SKILLS_CSV": str(PROJECT_ROOT / "data/ontology/skills.csv"),
        "COURSES_CSV": str(PROJECT_ROOT / "data/samples/courses.csv"),
        "MLFLOW_TRACKING_URI": f"file:{tracking_dir}",
        "MLFLOW_EXPERIMENT": "provider_behavior_test",
    }


class StartupTests(unittest.TestCase):
    def test_import_and_startup_load_metadata_without_calling_provider(self):
        script = dedent("""\
            from unittest.mock import patch

            with patch("dotenv.load_dotenv"), patch(
                "openai.OpenAI", side_effect=AssertionError("Unexpected provider client")
            ) as provider:
                from fastapi.testclient import TestClient
                from src.app import app

                with TestClient(app) as client:
                    health = client.get("/health")
                    roles = client.get("/roles")
                    people = client.get("/persons")
                    matches = client.get("/roles/matches", params={"person_id": "p100"})
                assert health.status_code == 200, health.text
                assert roles.status_code == 200 and roles.json(), roles.text
                assert people.status_code == 200, people.text
                assert any(person["person_id"] == "p100" for person in people.json())
                assert matches.status_code == 200 and matches.json() == [], matches.text
                provider.assert_not_called()
            """)
        with tempfile.TemporaryDirectory() as tracking_dir:
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=PROJECT_ROOT,
                env={**os.environ, **local_environment(tracking_dir)},
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tracking_dir = cls.enterClassContext(tempfile.TemporaryDirectory())
        cls.enterClassContext(patch.dict(os.environ, local_environment(tracking_dir)))
        with patch("dotenv.load_dotenv"):
            cls.utils = importlib.import_module("src.services.utils")
            with patch.object(
                cls.utils, "OpenAI", side_effect=AssertionError("Unexpected provider client")
            ):
                cls.api = importlib.import_module("src.app")
        cls.vector_store = importlib.import_module("src.services.vector_store")

    def setUp(self):
        graph = type(self.api.GRAPH)()
        self.enterContext(patch.object(self.api.GRAPH, "G", graph.G))
        self.enterContext(patch.object(self.vector_store.VECTOR_DB, "_store", {}))
        self.graph = self.api.GRAPH
        self.graph.upsert_person("fixture-person", name="Original")
        self.graph.upsert_skill("python", canonical_label="Python")
        self.graph.upsert_skill("sql", canonical_label="SQL")
        self.graph.add_person_skill("fixture-person", "python")
        self.graph.upsert_role("sql-role")
        self.graph.upsert_role("python-role")
        self.graph.add_role_skill("sql-role", "sql")
        self.graph.add_role_skill("python-role", "python")
        catalog = [
            {"role_id": "sql-role", "title": "SQL Role", "level": "IC"},
            {"role_id": "python-role", "title": "Python Role", "level": "IC"},
        ]
        self.enterContext(patch.object(self.api, "ROLE_CATALOG", catalog))
        self.provider = self.enterContext(patch.object(self.utils, "OpenAI"))
        self.sdk = self.provider.return_value.__enter__.return_value
        self.client = self.enterContext(TestClient(self.api.app))

    def matches(self, person_id="fixture-person"):
        return self.client.get("/roles/matches", params={"person_id": person_id})

    def assert_provider_error(self, response, expected_code):
        self.assertEqual(response.status_code, 503, response.text)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], expected_code)
        self.assertTrue(detail["message"])
        self.assertNotIn("offline-test-key", response.text)

    def test_missing_key_returns_service_unavailable(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            self.assert_provider_error(self.matches(), "provider_not_configured")
        self.provider.assert_not_called()

    def test_embedding_timeout_returns_service_unavailable(self):
        request = httpx.Request("POST", "https://example.invalid/embeddings")
        self.sdk.embeddings.create.side_effect = APITimeoutError(request)
        self.assert_provider_error(self.matches(), "provider_timeout")
        self.assert_provider_error(
            self.client.get("/recommendations/fixture-person"), "provider_timeout"
        )

    def test_embedding_rate_limit_returns_service_unavailable(self):
        request = httpx.Request("POST", "https://example.invalid/embeddings")
        response = httpx.Response(429, request=request)
        self.sdk.embeddings.create.side_effect = RateLimitError(
            "fixture throttled for offline-test-key", response=response, body=None
        )
        self.assert_provider_error(self.matches(), "provider_rate_limited")

    def test_incomplete_embeddings_return_service_unavailable(self):
        self.sdk.embeddings.create.return_value = SimpleNamespace(data=[])
        self.assert_provider_error(self.matches(), "provider_invalid_response")

    def test_malformed_embedding_http_response_returns_service_unavailable(self):
        for payload in (
            {"object": "list"},
            {"data": [None]},
            {"data": [{"index": 0, "embedding": [10**400]}]},
        ):
            with self.subTest(payload=payload):
                transport = httpx.MockTransport(
                    lambda request: httpx.Response(200, json=payload)
                )
                with OpenAI(api_key="offline-test-key", http_client=httpx.Client(transport=transport)) as sdk:
                    with patch.object(self.utils, "OpenAI", return_value=sdk):
                        self.assert_provider_error(self.matches(), "provider_invalid_response")

    def test_malformed_chat_response_does_not_ingest_profile(self):
        for payload in ({"choices": [{"message": None}]}, {"choices": {}}):
            with self.subTest(payload=payload):
                paths = []

                def malformed_chat(request):
                    paths.append(request.url.path)
                    return httpx.Response(200, json=payload)

                transport = httpx.MockTransport(malformed_chat)
                with OpenAI(api_key="offline-test-key", http_client=httpx.Client(transport=transport)) as sdk:
                    with patch.object(self.utils, "OpenAI", return_value=sdk):
                        response = self.client.post(
                            "/ingest/profile",
                            json={
                                "profile": {"person_id": "malformed-response-person"},
                                "evidence": [{"text": "Built a Python service"}],
                            },
                        )
                self.assert_provider_error(response, "provider_invalid_response")
                self.assertEqual(paths, ["/v1/chat/completions"])
        self.assertNotIn(("person", "malformed-response-person"), self.graph.G)
        self.assertFalse(self.vector_store.VECTOR_DB._store)

    def test_ingested_profile_gets_repeatable_role_ranking(self):
        evidence = "Automated data cleanup in Python"

        def fixture_embeddings(*, input, **_):
            vectors = {"python": [1.0, 0.0], "sql": [0.0, 1.0], evidence.lower(): [1.0, 0.0]}
            data = [
                SimpleNamespace(index=i, embedding=vectors[text.lower()])
                for i, text in enumerate(input)
            ]
            return SimpleNamespace(data=list(reversed(data)))

        self.sdk.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='["python"]'))]
        )
        self.sdk.embeddings.create.side_effect = fixture_embeddings
        ingested = self.client.post(
            "/ingest/profile",
            json={
                "profile": {"person_id": "fresh-person", "name": "Fixture"},
                "evidence": [{"text": evidence}],
            },
        )
        self.assertEqual(ingested.status_code, 200, ingested.text)
        self.assertEqual([skill["skill_id"] for skill in ingested.json()["skills_added"]], ["python"])
        self.assertIn("fresh-person_e_0", self.vector_store.VECTOR_DB._store)
        first = self.matches("fresh-person")
        second = self.matches("fresh-person")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(
            [match["role_id"] for match in first.json()], ["python-role", "sql-role"]
        )
        self.assertAlmostEqual(first.json()[0]["score"], 1.0)
        self.assertAlmostEqual(first.json()[1]["score"], 0.0)

    def test_ingest_failure_preserves_existing_profile_and_evidence(self):
        vector_db = self.vector_store.VECTOR_DB
        old_vector = np.array([1.0, 0.0])
        old_metadata = {"person_id": "fixture-person", "type": "evidence"}
        vector_db.upsert_embedding("fixture-person_e_0", old_vector, old_metadata)
        old_skills = self.graph.get_person_skills("fixture-person")

        self.sdk.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='["python"]'))]
        )
        request = httpx.Request("POST", "https://example.invalid/embeddings")
        self.sdk.embeddings.create.side_effect = APITimeoutError(request)
        response = self.client.post(
            "/ingest/profile",
            json={
                "profile": {"person_id": "fixture-person", "name": "Changed"},
                "evidence": [{"text": "Built dashboards using SQL"}],
            },
        )
        self.assert_provider_error(response, "provider_timeout")
        self.sdk.chat.completions.create.assert_called_once()
        self.sdk.embeddings.create.assert_called_once()
        self.assertEqual(self.graph.G.nodes[("person", "fixture-person")]["name"], "Original")
        self.assertEqual(self.graph.get_person_skills("fixture-person"), old_skills)
        self.assertEqual(list(vector_db._store), ["fixture-person_e_0"])
        embedding, metadata = vector_db._store["fixture-person_e_0"]
        np.testing.assert_array_equal(embedding, old_vector)
        self.assertEqual(metadata, old_metadata)
