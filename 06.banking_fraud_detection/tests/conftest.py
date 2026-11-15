"""Real PostgreSQL integration tests; never use the application's DATABASE_URL."""
import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
def disable_models(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from agents import base_agent

    def forbidden_client(*args, **kwargs):
        raise AssertionError("Tests must never construct a provider client")

    monkeypatch.setattr(base_agent, "OpenAI", forbidden_client)


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
            "Real PostgreSQL tests require pgserver: install requirements-dev.txt "
            "or set TEST_DATABASE_URL to a dedicated PostgreSQL test database."
        ) from exc
    server = pgserver.get_server(tmp_path_factory.mktemp("fraud-pg"), cleanup_mode="delete")
    try:
        yield server.get_uri()
    finally:
        server.cleanup()


@pytest.fixture
def database(postgres_url, monkeypatch):
    """Keep every test in a disposable schema, including with an external test DB."""
    admin = create_engine(postgres_url)
    schema = "fraud_test_" + uuid.uuid4().hex
    schema_created = False
    engine = None
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        schema_created = True
        engine = create_engine(
            postgres_url, connect_args={"options": f"-csearch_path={schema} -ctimezone=UTC"}
        )
        monkeypatch.setenv("DATABASE_URL", postgres_url)
        from db import db

        monkeypatch.setattr(db, "engine", engine)
        monkeypatch.setattr(db, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
        db.init_db()
        yield db
    finally:
        if engine is not None:
            engine.dispose()
        try:
            if schema_created:
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            admin.dispose()


@pytest.fixture
def client(database, monkeypatch):
    from fastapi.testclient import TestClient
    from api import server
    from orchestrator.fraud_orchestrator import FraudOrchestrator

    monkeypatch.setattr(server, "orchestrator", FraudOrchestrator())
    with TestClient(server.app) as client:
        yield client
