# db/db.py
from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, Float, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Dict, Any, Optional, List

def _default_sqlite_url() -> str:
    # Store sqlite DB in the project root (08.sales_qbr_builder/qbr_builder.sqlite)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sqlite_path = os.path.join(project_root, "qbr_builder.sqlite")
    return f"sqlite+pysqlite:///{sqlite_path}"

def _normalize_database_url(url: str) -> str:
    """
    Normalize postgres URLs to use psycopg (v3) driver for better Python 3.13+ support.
    """
    if url.startswith("postgres://"):
        # common alias; SQLAlchemy prefers postgresql
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        # Prefer psycopg v3 driver (psycopg)
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url

def _create_engine_with_fallback() -> "Any":
    """
    Create SQLAlchemy engine.
    - If DATABASE_URL points to Postgres but the driver isn't installed (common on Python 3.13),
      fall back to SQLite so the API can still run.
    """
    raw_url = os.getenv("DATABASE_URL", _default_sqlite_url())
    url = _normalize_database_url(raw_url)

    try:
        if url.startswith("sqlite"):
            return create_engine(
                url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
        return create_engine(url, pool_pre_ping=True)
    except ModuleNotFoundError as e:
        # Typical error: No module named 'psycopg2' or missing postgres driver
        fallback_url = _default_sqlite_url()
        return create_engine(
            fallback_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )

_engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
Base = declarative_base()

def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_with_fallback()
        SessionLocal.configure(bind=_engine)
    return _engine

# Models
class QBRRequest(Base):
    __tablename__ = "qbr_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    account_id = Column(String(64), nullable=False, index=True)
    account_name = Column(Text)
    quarter = Column(String(16))
    period_start = Column(Date)
    period_end = Column(Date)
    # Store as JSON for cross-db compatibility (SQLite fallback + Postgres)
    goals = Column(JSON)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QBRPack(Base):
    __tablename__ = "qbr_packs"
    
    id = Column(Integer, primary_key=True, index=True)
    qbr_request_id = Column(Integer, index=True)
    pack_id = Column(String(64), unique=True, nullable=False, index=True)
    executive_summary = Column(Text)
    account_health_score = Column(Float)
    version = Column(Integer, default=1)
    status = Column(String(32), default="draft", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime)
    exported_at = Column(DateTime)

class Insight(Base):
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    qbr_pack_id = Column(Integer, index=True)
    insight_type = Column(String(32), nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    impact_score = Column(Float)
    confidence_score = Column(Float)
    category = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    qbr_pack_id = Column(Integer, index=True)
    source_type = Column(String(32), nullable=False, index=True)
    source_name = Column(String(64))
    data_json = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    data_quality_score = Column(Float)

class ActionItem(Base):
    __tablename__ = "action_items"
    
    id = Column(Integer, primary_key=True, index=True)
    qbr_pack_id = Column(Integer, index=True)
    description = Column(Text, nullable=False)
    assignee = Column(Text)
    due_date = Column(Date)
    priority = Column(String(16), default="medium")
    status = Column(String(32), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class Approval(Base):
    __tablename__ = "approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    qbr_pack_id = Column(Integer, index=True)
    approver_name = Column(Text)
    action = Column(String(32), nullable=False)
    feedback = Column(Text)
    revision_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    qbr_pack_id = Column(Integer, index=True)
    metric_name = Column(String(64), nullable=False)
    metric_value = Column(Float)
    metric_unit = Column(String(32))
    period_start = Column(Date)
    period_end = Column(Date)
    comparison_period_start = Column(Date)
    comparison_period_end = Column(Date)
    comparison_value = Column(Float)
    change_percent = Column(Float)
    trend = Column(String(16))
    created_at = Column(DateTime, default=datetime.utcnow)

# Orchestrator runtime / audit log tables
class QBRRun(Base):
    __tablename__ = "qbr_runs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), index=True)
    pack_id = Column(String(64), index=True)
    status = Column(String(32), default="running", index=True)  # running | completed | failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QBREvent(Base):
    __tablename__ = "qbr_events"

    id = Column(Integer, primary_key=True, index=True)
    qbr_run_id = Column(Integer, index=True)
    step = Column(String(64), index=True)
    event_type = Column(String(32), index=True)  # started | completed | error | checkpoint
    payload_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=get_engine())

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations"""
    # Ensure engine is initialized and SessionLocal bound
    get_engine()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def upsert_qbr_request(session: Session, data: Dict[str, Any]) -> QBRRequest:
    """Create or update a QBR request"""
    request = session.query(QBRRequest).filter_by(request_id=data["request_id"]).first()
    if request:
        for key, value in data.items():
            setattr(request, key, value)
        request.updated_at = datetime.utcnow()
    else:
        request = QBRRequest(**data)
        session.add(request)
    return request

def create_qbr_pack(session: Session, data: Dict[str, Any]) -> QBRPack:
    """Create a QBR pack"""
    pack = QBRPack(**data)
    session.add(pack)
    return pack

def insert_insight(session: Session, data: Dict[str, Any]) -> Insight:
    """Insert an insight"""
    insight = Insight(**data)
    session.add(insight)
    return insight

def insert_data_source(session: Session, data: Dict[str, Any]) -> DataSource:
    """Insert a data source"""
    data_source = DataSource(**data)
    session.add(data_source)
    return data_source

def insert_action_item(session: Session, data: Dict[str, Any]) -> ActionItem:
    """Insert an action item"""
    action_item = ActionItem(**data)
    session.add(action_item)
    return action_item

def insert_approval(session: Session, data: Dict[str, Any]) -> Approval:
    """Insert an approval record"""
    approval = Approval(**data)
    session.add(approval)
    return approval

def insert_metric(session: Session, data: Dict[str, Any]) -> Metric:
    """Insert a metric"""
    metric = Metric(**data)
    session.add(metric)
    return metric


def create_qbr_run(session: Session, request_id: str, pack_id: str) -> QBRRun:
    run = QBRRun(request_id=request_id, pack_id=pack_id, status="running")
    session.add(run)
    session.flush()
    return run


def update_qbr_run_status(session: Session, qbr_run_id: int, status: str) -> None:
    run = session.query(QBRRun).filter_by(id=qbr_run_id).first()
    if run:
        run.status = status
        run.updated_at = datetime.utcnow()


def insert_qbr_event(session: Session, qbr_run_id: int, step: str, event_type: str, payload: Dict[str, Any]) -> QBREvent:
    ev = QBREvent(qbr_run_id=qbr_run_id, step=step, event_type=event_type, payload_json=payload)
    session.add(ev)
    return ev
