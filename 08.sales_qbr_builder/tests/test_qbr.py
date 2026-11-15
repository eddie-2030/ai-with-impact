import json
import os
import tempfile
import unittest
from datetime import date
from itertools import chain, repeat
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import server
from db import db
from models import qbr_analyzer
from orchestrator import qbr_orchestrator as runtime


PERIOD_START = date(2025, 1, 1)
PERIOD_END = date(2025, 3, 31)
STAGES = ("plan", "fetch_data", "aggregate_validate", "generate_insights", "finalize")
TRACE = [
    ("plan", "started"),
    ("plan", "completed"),
    ("fetch_data", "started"),
    ("fetch_data", "checkpoint"),
    ("fetch_data", "checkpoint"),
    ("fetch_data", "checkpoint"),
    ("fetch_data", "completed"),
    ("aggregate_validate", "started"),
    ("aggregate_validate", "checkpoint"),
    ("aggregate_validate", "completed"),
    ("generate_insights", "started"),
    ("generate_insights", "checkpoint"),
    ("generate_insights", "completed"),
    ("finalize", "started"),
    ("finalize", "completed"),
]


class OrchestrationTests(unittest.TestCase):
    def test_langgraph_uses_one_snapshot_per_run(self):
        self.assert_one_snapshot(sequential=False)

    def test_sequential_fallback_uses_one_snapshot_per_run(self):
        self.assert_one_snapshot(sequential=True)

    def assert_one_snapshot(self, sequential):
        ctx = runtime.QBRContext(
            request_id="qbr-test",
            pack_id="pack-test",
            account_id="acc-mixed-001",
            account_name="Example Account",
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            goals=["Renewal"],
        )
        crm = {"arr": 2000, "crm_revision_1": True}
        analytics = {"mrr": 100, "analytics_revision_1": True}
        support = {"support_revision_1": True}
        response = {
            "executive_summary": "Fixture summary",
            "action_items": [{"description": "Schedule a review"}],
            "metrics": [{"name": "Active users", "value": 42}],
        }

        fetch_crm = self.enterContext(
            patch.object(
                runtime,
                "fetch_crm_data",
                side_effect=chain((crm,), repeat({"crm_revision_2": True})),
            )
        )
        fetch_analytics = self.enterContext(
            patch.object(
                runtime,
                "fetch_analytics_data",
                side_effect=chain((analytics,), repeat({"analytics_revision_2": True})),
            )
        )
        fetch_support = self.enterContext(
            patch.object(
                runtime,
                "fetch_support_data",
                side_effect=chain((support,), repeat({"support_revision_2": True})),
            )
        )
        aggregate = self.enterContext(
            patch.object(runtime, "aggregate_qbr_data", wraps=runtime.aggregate_qbr_data)
        )
        generate = self.enterContext(patch.object(runtime, "generate_qbr_insights", return_value=response))
        orchestrator = runtime.QBROrchestrator(ctx)
        if sequential:
            orchestrator._graph = None
        else:
            self.assertIsNotNone(orchestrator._graph)

        events = []
        with self.assertRaises(StopIteration) as stop:
            run = orchestrator.run()
            self.addCleanup(run.close)
            while True:
                event = next(run)
                events.append(event)
                if (event.step, event.event_type) == ("fetch_data", "started"):
                    fetch_crm.assert_not_called()
                    fetch_analytics.assert_not_called()
                    fetch_support.assert_not_called()
                elif (event.step, event.event_type) == ("generate_insights", "started"):
                    generate.assert_not_called()

        for fetch in (fetch_crm, fetch_analytics, fetch_support):
            fetch.assert_called_once_with(ctx.account_id, PERIOD_START, PERIOD_END)
        aggregate.assert_called_once_with(crm, analytics, support)
        result = stop.exception.value
        self.assertEqual(result["crm_data"], crm)
        self.assertEqual(result["analytics_data"], analytics)
        self.assertEqual(result["support_data"], support)
        generate.assert_called_once_with(
            account_name=ctx.account_name,
            aggregated_data=result["aggregated_data"],
            goals=ctx.goals,
            period_start=PERIOD_START,
            period_end=PERIOD_END,
        )
        self.assertEqual(result["aggregated_data"]["crm"], crm)
        self.assertEqual(result["aggregated_data"]["analytics"], analytics)
        self.assertEqual(result["aggregated_data"]["support"], support)
        self.assertEqual(
            result["insights_result"]["action_items"][0]["assignee"],
            "Customer Success Manager",
        )

        trace = [(event.step, event.event_type) for event in events]
        if sequential:
            self.assertEqual(trace.pop(0), ("plan", "checkpoint"))
        self.assertEqual(trace, TRACE)
        sources = [
            (event.payload["source"], set(event.payload["keys"]))
            for event in events
            if (event.step, event.event_type) == ("fetch_data", "checkpoint")
        ]
        self.assertEqual(
            sources,
            [("crm", set(crm)), ("analytics", set(analytics)), ("support", set(support))],
        )
        checkpoints = {
            event.step: event.payload
            for event in events
            if event.event_type == "checkpoint" and event.step in {"aggregate_validate", "generate_insights"}
        }
        self.assertTrue(result["aggregated_data"]["data_quality_warnings"])
        self.assertEqual(
            checkpoints["aggregate_validate"]["warnings"],
            result["aggregated_data"]["data_quality_warnings"],
        )
        self.assertEqual(checkpoints["generate_insights"]["action_items_count"], 1)
        self.assertEqual(checkpoints["generate_insights"]["metrics_count"], 1)


class QBRApiTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        engine = create_engine(f"sqlite+pysqlite:///{Path(directory) / 'qbr.sqlite'}")
        self.addCleanup(engine.dispose)
        self.sessions = sessionmaker(bind=engine)
        self.enterContext(patch.object(db, "_engine", engine))
        self.enterContext(patch.object(db, "SessionLocal", self.sessions))
        self.enterContext(patch.dict(os.environ, {"OPENAI_API_KEY": ""}))
        self.client = self.enterContext(TestClient(server.app))

    def generate(self):
        response = self.client.post(
            "/qbr/generate",
            json={
                "account_id": "acc-mixed-001",
                "account_name": "Example Account",
                "quarter": "Q1-2025",
                "period_start": PERIOD_START.isoformat(),
                "period_end": PERIOD_END.isoformat(),
                "goals": ["Renewal", "Product Adoption"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        accepted = response.json()
        self.assertEqual(accepted["status"], "processing")
        return accepted

    def get(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_generate_persists_linked_pack_sources_and_ordered_trace(self):
        self.assertEqual(self.get("/health")["status"], "healthy")
        accepted = self.generate()
        path = f"/qbr/{accepted['pack_id']}"
        pack = self.get(path)
        self.assertEqual(pack["status"], "pending_approval")
        self.assertIn("Example Account", pack["executive_summary"])
        self.assertTrue(pack["insights"])
        self.assertTrue(pack["action_items"])
        self.assertTrue(pack["metrics"])
        trace = self.get(path + "/events")
        self.assertEqual(trace["run"]["status"], "completed")
        self.assertEqual(
            [(event["step"], event["event_type"]) for event in trace["events"]],
            TRACE,
        )
        with self.sessions() as session:
            saved = session.scalar(select(db.QBRPack).filter_by(pack_id=pack["pack_id"]))
            request = session.scalar(
                select(db.QBRRequest).filter_by(request_id=accepted["request_id"])
            )
            self.assertEqual(request.status, "completed")
            self.assertEqual(saved.qbr_request_id, request.id)
            sources = {
                row.source_type: row.data_json
                for row in session.scalars(select(db.DataSource).filter_by(qbr_pack_id=saved.id))
            }
            self.assertEqual(set(sources), {"crm", "analytics", "support"})
            self.assertEqual(sources["crm"]["account_id"], request.account_id)
        for event in trace["events"]:
            if event["step"] == "fetch_data" and event["event_type"] == "checkpoint":
                payload = event["payload"]
                self.assertEqual(set(payload["keys"]), set(sources[payload["source"]]))

    def test_failed_graph_persists_one_error_and_no_pack_output(self):
        with patch.object(
            runtime,
            "generate_qbr_insights",
            side_effect=RuntimeError("private fixture error"),
        ):
            accepted = self.generate()
        trace = self.assert_failed_generation(accepted)
        self.assertEqual(
            [event["step"] for event in trace["events"] if event["event_type"] == "started"],
            list(STAGES[:-1]),
        )
        self.assertNotIn("private fixture error", str(trace))

    def test_failed_output_write_rolls_back_all_pack_output(self):
        with patch.object(server, "insert_metric", side_effect=RuntimeError("fixture write failure")):
            accepted = self.generate()
        self.assert_failed_generation(accepted)

    def test_approval_applies_only_once_after_generation(self):
        attempted = []
        original = runtime.generate_qbr_insights

        def during_generation(**kwargs):
            with self.sessions() as session:
                pack = session.scalar(select(db.QBRPack))
                path = f"/qbr/{pack.pack_id}"
            attempted.append(self.client.post(path + "/approve", json={"action": "approve"}))
            attempted.append(self.client.post(path + "/revise", json={"feedback": "Try again"}))
            return original(**kwargs)

        with patch.object(runtime, "generate_qbr_insights", side_effect=during_generation):
            accepted = self.generate()
        self.assertEqual([response.status_code for response in attempted], [409, 409])
        path = f"/qbr/{accepted['pack_id']}/approve"
        approved = self.client.post(path, json={"action": "approve"})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "approved")
        self.assertEqual(self.client.post(path, json={"action": "reject"}).status_code, 409)
        with self.sessions() as session:
            self.assertEqual(len(list(session.scalars(select(db.Approval)))), 1)

    def test_provider_invalid_due_date_uses_heuristics_and_marks_trace(self):
        response = {"action_items": [{"description": "Follow up", "due_date": "next week"}]}
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(response)))]
        )
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-key"}),
            patch.object(qbr_analyzer, "_get_openai_client", return_value=client),
        ):
            accepted = self.generate()
        client.chat.completions.create.assert_called_once()
        path = f"/qbr/{accepted['pack_id']}"
        pack = self.get(path)
        self.assertEqual(pack["status"], "pending_approval")
        self.assertIn("Example Account", pack["executive_summary"])
        events = self.get(path + "/events")["events"]
        generated = next(
            event for event in events
            if (event["step"], event["event_type"]) == ("generate_insights", "checkpoint")
        )
        self.assertTrue(generated["payload"]["has_error"])

    def assert_failed_generation(self, accepted):
        path = f"/qbr/{accepted['pack_id']}"
        pack = self.get(path)
        self.assertEqual(pack["status"], "failed")
        self.assertEqual(pack["insights"], [])
        self.assertEqual(pack["action_items"], [])
        self.assertEqual(pack["metrics"], [])
        self.assertIsNone(pack["account_health_score"])
        trace = self.get(path + "/events")
        self.assertEqual(trace["run"]["status"], "failed")
        errors = [event for event in trace["events"] if event["event_type"] == "error"]
        self.assertEqual(len(errors), 1)
        with self.sessions() as session:
            request = session.scalar(
                select(db.QBRRequest).filter_by(request_id=accepted["request_id"])
            )
            self.assertEqual(request.status, "failed")
            self.assertEqual(list(session.scalars(select(db.DataSource))), [])
        return trace
