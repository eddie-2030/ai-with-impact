# db/db.py
from __future__ import annotations
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import JSONB
from contextlib import contextmanager
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/code_reviewer")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CodeReview(Base):
    __tablename__ = "code_reviews"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(String(64), unique=True, nullable=False)
    code_content = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    file_path = Column(String(255))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    security_findings = relationship("SecurityFinding", back_populates="review", cascade="all, delete-orphan")
    performance_findings = relationship("PerformanceFinding", back_populates="review", cascade="all, delete-orphan")
    quality_findings = relationship("QualityFinding", back_populates="review", cascade="all, delete-orphan")
    code_rewrites = relationship("CodeRewrite", back_populates="review", cascade="all, delete-orphan")
    review_summary = relationship("ReviewSummary", back_populates="review", uselist=False, cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="review", cascade="all, delete-orphan")

class SecurityFinding(Base):
    __tablename__ = "security_findings"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("code_reviews.id"))
    finding_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    cwe_id = Column(String(20))
    owasp_category = Column(String(50))
    description = Column(Text, nullable=False)
    line_number = Column(Integer)
    code_snippet = Column(Text)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    review = relationship("CodeReview", back_populates="security_findings")

class PerformanceFinding(Base):
    __tablename__ = "performance_findings"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("code_reviews.id"))
    finding_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    line_number = Column(Integer)
    code_snippet = Column(Text)
    current_complexity = Column(String(20))
    suggested_complexity = Column(String(20))
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    review = relationship("CodeReview", back_populates="performance_findings")

class QualityFinding(Base):
    __tablename__ = "quality_findings"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("code_reviews.id"))
    finding_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    line_number = Column(Integer)
    code_snippet = Column(Text)
    metric_value = Column(Float)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    review = relationship("CodeReview", back_populates="quality_findings")

class CodeRewrite(Base):
    __tablename__ = "code_rewrites"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("code_reviews.id"))
    finding_id = Column(Integer)
    finding_type = Column(String(50))
    original_code = Column(Text, nullable=False)
    rewritten_code = Column(Text, nullable=False)
    explanation = Column(Text)
    confidence_score = Column(Float)
    rewrite_mode = Column(String(20), default="suggest")
    applied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    review = relationship("CodeReview", back_populates="code_rewrites")

class ReviewSummary(Base):
    __tablename__ = "review_summaries"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("code_reviews.id"))
    security_score = Column(Float)
    performance_score = Column(Float)
    quality_score = Column(Float)
    overall_score = Column(Float)
    total_findings = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    high_findings = Column(Integer, default=0)
    medium_findings = Column(Integer, default=0)
    low_findings = Column(Integer, default=0)
    summary_text = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    review = relationship("CodeReview", back_populates="review_summary")

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("code_reviews.id"))
    agent_type = Column(String(50), nullable=False)
    execution_status = Column(String(20), default="pending")
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    review = relationship("CodeReview", back_populates="agent_executions")

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

