# db/db.py
from __future__ import annotations
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Date, ARRAY, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import JSONB
from contextlib import contextmanager
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/research_writer")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ResearchRequest(Base):
    __tablename__ = "research_requests"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(64), unique=True)
    research_query = Column(Text, nullable=False)
    research_type = Column(String(50), default="comprehensive")
    status = Column(String(50), default="pending")
    max_sources = Column(Integer, default=20)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    sources = relationship("Source", back_populates="research_request", cascade="all, delete-orphan")
    findings = relationship("ResearchFinding", back_populates="research_request", cascade="all, delete-orphan")
    report = relationship("ResearchReport", back_populates="research_request", uselist=False, cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="research_request", cascade="all, delete-orphan")

class Source(Base):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(String(64), unique=True)
    research_request_id = Column(Integer, ForeignKey("research_requests.id"))
    title = Column(Text, nullable=False)
    authors = Column(ARRAY(String))
    publication_date = Column(Date)
    url = Column(Text)
    doi = Column(Text)
    source_type = Column(String(50))
    publisher = Column(Text)
    access_date = Column(Date)
    credibility_score = Column(Float, default=0.0)
    verification_status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    research_request = relationship("ResearchRequest", back_populates="sources")
    findings = relationship("ResearchFinding", back_populates="source", cascade="all, delete-orphan")
    verification = relationship("SourceVerification", back_populates="source", uselist=False, cascade="all, delete-orphan")

class ResearchFinding(Base):
    __tablename__ = "research_findings"
    
    id = Column(Integer, primary_key=True)
    research_request_id = Column(Integer, ForeignKey("research_requests.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))
    content = Column(Text, nullable=False)
    quote = Column(Text)
    page_number = Column(String(20))
    in_text_citation = Column(Text)
    confidence_score = Column(Float, default=0.5)
    agent_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    research_request = relationship("ResearchRequest", back_populates="findings")
    source = relationship("Source", back_populates="findings")

class SourceVerification(Base):
    __tablename__ = "source_verifications"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    url_valid = Column(Boolean)
    domain_reputation = Column(Text)
    author_verified = Column(Boolean)
    peer_reviewed = Column(Boolean)
    cross_reference_count = Column(Integer, default=0)
    consensus_level = Column(String(20))
    verification_details = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    source = relationship("Source", back_populates="verification")

class ResearchReport(Base):
    __tablename__ = "research_reports"
    
    id = Column(Integer, primary_key=True)
    research_request_id = Column(Integer, ForeignKey("research_requests.id"))
    report_content = Column(Text, nullable=False)
    executive_summary = Column(Text)
    references_section = Column(Text)
    word_count = Column(Integer)
    source_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    research_request = relationship("ResearchRequest", back_populates="report")

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True)
    research_request_id = Column(Integer, ForeignKey("research_requests.id"))
    agent_type = Column(String(50), nullable=False)
    execution_status = Column(String(20), default="pending")
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    execution_time_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    research_request = relationship("ResearchRequest", back_populates="agent_executions")

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


