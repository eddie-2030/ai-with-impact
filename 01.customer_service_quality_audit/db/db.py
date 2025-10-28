# db/db.py
from __future__ import annotations
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/cxqa")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    agent_ext_id = Column(String(64), unique=True)
    name = Column(Text)
    conversations = relationship("Conversation", back_populates="agent")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    conv_ext_id = Column(String(64), unique=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    started_at = Column(DateTime)
    channel = Column(String(16))
    language = Column(String(16))
    raw_text = Column(Text)
    redacted_text = Column(Text)
    agent = relationship("Agent", back_populates="conversations")
    scores = relationship("Score", back_populates="conversation", cascade="all, delete-orphan")

class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"))
    model_version = Column(Text)
    professionalism = Column(Float)
    friendliness = Column(Float)
    resolution_effectiveness = Column(Float)
    explanation = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="scores")

class HumanLabel(Base):
    __tablename__ = "human_labels"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"))
    professionalism = Column(Integer)
    friendliness = Column(Integer)
    resolution_effectiveness = Column(Integer)
    notes = Column(Text)
    labeled_by = Column(Text)
    labeled_at = Column(DateTime, default=datetime.utcnow)

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    Base.metadata.create_all(bind=engine)

def upsert_agent(session, agent_ext_id: str, name: Optional[str] = None) -> Agent:
    agent = session.query(Agent).filter_by(agent_ext_id=agent_ext_id).first()
    if not agent:
        agent = Agent(agent_ext_id=agent_ext_id, name=name)
        session.add(agent)
        session.flush()
    return agent

def insert_conversation(session, conv: Dict[str, Any]) -> Conversation:
    c = Conversation(**conv)
    session.add(c)
    session.flush()
    return c

def insert_score(session, score: Dict[str, Any]) -> Score:
    s = Score(**score)
    session.add(s)
    session.flush()
    return s
