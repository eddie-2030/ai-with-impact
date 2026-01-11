# db/db.py
from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, Float, ARRAY, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Dict, Any, Optional, List

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/qbr_builder")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    goals = Column(ARRAY(Text))
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

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations"""
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
