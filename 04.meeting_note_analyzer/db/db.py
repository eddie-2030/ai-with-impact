# db/db.py
from __future__ import annotations
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Date, ARRAY, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from contextlib import contextmanager
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/meeting_analyzer")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True)
    meeting_ext_id = Column(String(64), unique=True)
    title = Column(Text)
    date = Column(DateTime)
    participants = Column(ARRAY(String))
    transcript = Column(Text)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="meeting", cascade="all, delete-orphan")
    participant_contributions = relationship("ParticipantContribution", back_populates="meeting", cascade="all, delete-orphan")

class ActionItem(Base):
    __tablename__ = "action_items"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    description = Column(Text, nullable=False)
    assignee = Column(Text)
    due_date = Column(Date)
    status = Column(String(32), default="open")
    priority = Column(String(16), default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    meeting = relationship("Meeting", back_populates="action_items")

class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    decision_text = Column(Text, nullable=False)
    rationale = Column(Text)
    decision_maker = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    meeting = relationship("Meeting", back_populates="decisions")

class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    topic_text = Column(Text, nullable=False)
    relevance_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    meeting = relationship("Meeting", back_populates="topics")

class ParticipantContribution(Base):
    __tablename__ = "participant_contributions"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    participant_name = Column(Text, nullable=False)
    contribution_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    meeting = relationship("Meeting", back_populates="participant_contributions")

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

def upsert_meeting(session: Session, meeting_data: dict) -> Meeting:
    """Create or update a meeting"""
    meeting = session.query(Meeting).filter_by(meeting_ext_id=meeting_data["meeting_ext_id"]).first()
    if not meeting:
        meeting = Meeting(**meeting_data)
        session.add(meeting)
    else:
        for key, value in meeting_data.items():
            setattr(meeting, key, value)
    return meeting

def insert_action_item(session: Session, action_item_data: dict) -> ActionItem:
    """Insert an action item"""
    action_item = ActionItem(**action_item_data)
    session.add(action_item)
    return action_item

def insert_decision(session: Session, decision_data: dict) -> Decision:
    """Insert a decision"""
    decision = Decision(**decision_data)
    session.add(decision)
    return decision

def insert_topic(session: Session, topic_data: dict) -> Topic:
    """Insert a topic"""
    topic = Topic(**topic_data)
    session.add(topic)
    return topic

def insert_participant_contribution(session: Session, contribution_data: dict) -> ParticipantContribution:
    """Insert or update participant contribution"""
    contribution = session.query(ParticipantContribution).filter_by(
        meeting_id=contribution_data["meeting_id"],
        participant_name=contribution_data["participant_name"]
    ).first()
    
    if not contribution:
        contribution = ParticipantContribution(**contribution_data)
        session.add(contribution)
    else:
        contribution.contribution_count += contribution_data.get("contribution_count", 0)
        contribution.word_count += contribution_data.get("word_count", 0)
    
    return contribution

