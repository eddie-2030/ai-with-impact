"""Real PostgreSQL fixtures that never use the application's default database."""
from copy import deepcopy
import importlib
import os
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema


@pytest.fixture(scope="session")
def postgres_url(tmp_path_factory):
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        if make_url(url).get_backend_name() != "postgresql":
            raise pytest.UsageError("TEST_DATABASE_URL must point to a dedicated PostgreSQL test database")
        yield url
        return

    try:
        import pgserver
    except ImportError as exc:
        raise pytest.UsageError(
            "Install requirements-dev.txt or set TEST_DATABASE_URL to a dedicated PostgreSQL test database"
        ) from exc

    server = pgserver.get_server(
        Path(tmp_path_factory.mktemp("meeting-postgres")) / "pgdata",
        cleanup_mode="delete",
    )
    try:
        yield server.get_uri()
    finally:
        server.cleanup()


@pytest.fixture
def db(postgres_url, monkeypatch):
    """Use a fresh schema per test, including for API startup/table creation."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    database = importlib.import_module("db.db")
    schema = f"meeting_test_{uuid4().hex}"
    admin_engine = create_engine(postgres_url)
    with admin_engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    test_engine = create_engine(
        postgres_url, connect_args={"options": f"-csearch_path={schema}"}
    )
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(
        database,
        "SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=test_engine),
    )
    try:
        database.init_db()
        yield database
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()


@pytest.fixture
def analysis():
    return {
        "summary": "Alice will publish the roadmap after approval.",
        "action_items": [{
            "description": "Publish the roadmap",
            "assignee": "Alice",
            "due_date": "2026-11-06",
            "priority": "high",
        }],
        "decisions": [{
            "decision_text": "Approve the roadmap",
            "rationale": "The milestones are agreed",
            "decision_maker": "Alice",
        }],
        "topics": [{"topic_text": "Roadmap", "relevance_score": 0.9}],
        "participant_contributions": {
            "Alice": {"contribution_count": 2, "word_count": 15}
        },
    }


@pytest.fixture
def follow_ups():
    return [{"item": "Review delivery", "reason": "Track progress", "suggested_timeline": "Next week"}]


@pytest.fixture
def analysis_provider(analysis, follow_ups, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    analyzer = importlib.import_module("models.meeting_analyzer")

    def no_model_client():
        raise AssertionError("Tests must not make model requests")

    monkeypatch.setattr(analyzer, "_get_client", no_model_client)
    service = importlib.import_module("services.meetings")
    analysis["follow_ups"] = follow_ups
    provider = Mock(side_effect=lambda **kwargs: deepcopy(analysis))
    monkeypatch.setattr(service, "analyze_meeting", provider)
    return provider


@pytest.fixture
def entrypoints(db, analysis_provider):
    return importlib.import_module("api.server"), importlib.import_module("pipeline.process_meetings")


@pytest.fixture
def meeting_record():
    return {
        "meeting_id": "roadmap-planning",
        "title": "Roadmap planning",
        "date": "2026-11-02T10:00:00",
        "participants": ["Alice"],
        "transcript": "Alice: The roadmap is approved. I will publish it by Friday.",
    }
