# db/db.py
from __future__ import annotations
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Date, ARRAY, Float, Boolean, ForeignKey, DECIMAL, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import JSONB
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fraud_detection")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), unique=True, nullable=False)
    account_number = Column(String(64))
    email = Column(String(255))
    phone = Column(String(20))
    registration_date = Column(Date)
    account_status = Column(String(20), default="active")
    risk_profile = Column(String(20), default="low")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("FraudAlert", back_populates="user", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(64), unique=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.user_id"))
    amount = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    merchant = Column(String(255))
    merchant_category = Column(String(50))
    location = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    device_id = Column(String(64))
    ip_address = Column(String(45))
    transaction_type = Column(String(50))
    payment_method = Column(String(50))
    timestamp = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")
    risk_assessment = relationship("RiskAssessment", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("FraudAlert", back_populates="transaction", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="transaction", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), ForeignKey("users.user_id"))
    avg_transaction_amount = Column(DECIMAL(15, 2))
    typical_merchants = Column(ARRAY(String))
    typical_locations = Column(ARRAY(String))
    typical_transaction_times = Column(ARRAY(Time))
    spending_pattern = Column(JSONB)
    device_fingerprints = Column(ARRAY(String))
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="profile")

class FraudPattern(Base):
    __tablename__ = "fraud_patterns"
    
    id = Column(Integer, primary_key=True)
    pattern_name = Column(String(100), nullable=False)
    pattern_type = Column(String(50))
    description = Column(Text)
    detection_rules = Column(JSONB)
    ml_model_path = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id"))
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    risk_factors = Column(JSONB)
    agent_analysis = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("Transaction", back_populates="risk_assessment")

class FraudAlert(Base):
    __tablename__ = "fraud_alerts"
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(String(64), unique=True, nullable=False)
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id"))
    user_id = Column(String(64), ForeignKey("users.user_id"))
    alert_type = Column(String(50))
    severity = Column(String(20), nullable=False)
    risk_score = Column(Float, nullable=False)
    status = Column(String(20), default="open")
    description = Column(Text)
    investigation_notes = Column(Text)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transaction = relationship("Transaction", back_populates="alerts")
    user = relationship("User", back_populates="alerts")
    investigation_case = relationship("InvestigationCase", back_populates="alert", uselist=False, cascade="all, delete-orphan")

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id"))
    agent_type = Column(String(50), nullable=False)
    execution_status = Column(String(20), default="pending")
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    transaction = relationship("Transaction", back_populates="agent_executions")

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    
    id = Column(Integer, primary_key=True)
    case_id = Column(String(64), unique=True, nullable=False)
    alert_id = Column(String(64), ForeignKey("fraud_alerts.alert_id"))
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id"))
    investigator = Column(String(100))
    case_status = Column(String(20), default="open")
    findings = Column(Text)
    decision = Column(String(50))
    resolution_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    alert = relationship("FraudAlert", back_populates="investigation_case")

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

def upsert_user(session: Session, user_data: dict) -> User:
    """Create or update a user"""
    user = session.query(User).filter_by(user_id=user_data["user_id"]).first()
    if not user:
        user = User(**user_data)
        session.add(user)
    else:
        for key, value in user_data.items():
            setattr(user, key, value)
    return user

def insert_transaction(session: Session, transaction_data: dict) -> Transaction:
    """Insert a transaction"""
    transaction = Transaction(**transaction_data)
    session.add(transaction)
    return transaction

def insert_risk_assessment(session: Session, assessment_data: dict) -> RiskAssessment:
    """Insert a risk assessment"""
    assessment = RiskAssessment(**assessment_data)
    session.add(assessment)
    return assessment

def insert_fraud_alert(session: Session, alert_data: dict) -> FraudAlert:
    """Insert a fraud alert"""
    alert = FraudAlert(**alert_data)
    session.add(alert)
    return alert

