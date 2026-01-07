# api/server.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from db.db import session_scope, init_db, upsert_meeting, insert_action_item, insert_decision, insert_topic, insert_participant_contribution
from models.meeting_analyzer import analyze_meeting, extract_follow_ups
import os

app = FastAPI(title="Meeting Notes Analyzer API", version="1.0")

class MeetingIn(BaseModel):
    meeting_id: str
    title: Optional[str] = None
    date: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    transcript: str = Field(..., min_length=10)

class ActionItemOut(BaseModel):
    id: int
    description: str
    assignee: Optional[str]
    due_date: Optional[date]
    status: str
    priority: str

class DecisionOut(BaseModel):
    id: int
    decision_text: str
    rationale: Optional[str]
    decision_maker: Optional[str]

class TopicOut(BaseModel):
    id: int
    topic_text: str
    relevance_score: Optional[float]

class MeetingAnalysisOut(BaseModel):
    meeting_id: str
    summary: str
    action_items: List[ActionItemOut]
    decisions: List[DecisionOut]
    topics: List[TopicOut]
    follow_ups: List[Dict[str, Any]]

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/analyze")
async def analyze(meeting: MeetingIn) -> Dict[str, Any]:
    """Analyze a meeting transcript and extract structured information"""
    
    # Analyze meeting using LLM
    analysis = analyze_meeting(
        transcript=meeting.transcript,
        participants=meeting.participants,
        title=meeting.title
    )
    
    # Extract follow-ups
    follow_ups = extract_follow_ups(meeting.transcript, meeting.participants)
    
    # Parse meeting date
    meeting_date = None
    if meeting.date:
        try:
            meeting_date = datetime.fromisoformat(meeting.date.replace('Z', '+00:00'))
        except:
            pass
    
    # Store in database
    with session_scope() as s:
        db_meeting = upsert_meeting(s, {
            "meeting_ext_id": meeting.meeting_id,
            "title": meeting.title,
            "date": meeting_date,
            "participants": meeting.participants,
            "transcript": meeting.transcript,
            "summary": analysis.get("summary", "")
        })
        
        # Store action items
        action_items = []
        for ai in analysis.get("action_items", []):
            due_date = None
            if ai.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(ai["due_date"]).date()
                except:
                    pass
            
            db_ai = insert_action_item(s, {
                "meeting_id": db_meeting.id,
                "description": ai.get("description", ""),
                "assignee": ai.get("assignee"),
                "due_date": due_date,
                "priority": ai.get("priority", "medium"),
                "status": "open"
            })
            action_items.append({
                "id": db_ai.id,
                "description": db_ai.description,
                "assignee": db_ai.assignee,
                "due_date": db_ai.due_date.isoformat() if db_ai.due_date else None,
                "status": db_ai.status,
                "priority": db_ai.priority
            })
        
        # Store decisions
        decisions = []
        for dec in analysis.get("decisions", []):
            db_dec = insert_decision(s, {
                "meeting_id": db_meeting.id,
                "decision_text": dec.get("decision_text", ""),
                "rationale": dec.get("rationale"),
                "decision_maker": dec.get("decision_maker")
            })
            decisions.append({
                "id": db_dec.id,
                "decision_text": db_dec.decision_text,
                "rationale": db_dec.rationale,
                "decision_maker": db_dec.decision_maker
            })
        
        # Store topics
        topics = []
        for topic in analysis.get("topics", []):
            db_topic = insert_topic(s, {
                "meeting_id": db_meeting.id,
                "topic_text": topic.get("topic_text", ""),
                "relevance_score": topic.get("relevance_score")
            })
            topics.append({
                "id": db_topic.id,
                "topic_text": db_topic.topic_text,
                "relevance_score": db_topic.relevance_score
            })
        
        # Store participant contributions
        for participant, contrib in analysis.get("participant_contributions", {}).items():
            insert_participant_contribution(s, {
                "meeting_id": db_meeting.id,
                "participant_name": participant,
                "contribution_count": contrib.get("contribution_count", 0),
                "word_count": contrib.get("word_count", 0)
            })
    
    return {
        "meeting_id": meeting.meeting_id,
        "summary": analysis.get("summary", ""),
        "action_items": action_items,
        "decisions": decisions,
        "topics": topics,
        "follow_ups": follow_ups
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "meeting-analyzer"}

@app.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    """Get meeting analysis by meeting_id"""
    from db.db import SessionLocal, Meeting
    
    session = SessionLocal()
    try:
        meeting = session.query(Meeting).filter_by(meeting_ext_id=meeting_id).first()
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        return {
            "meeting_id": meeting.meeting_ext_id,
            "title": meeting.title,
            "date": meeting.date.isoformat() if meeting.date else None,
            "participants": meeting.participants,
            "summary": meeting.summary,
            "action_items": [{"id": ai.id, "description": ai.description, "assignee": ai.assignee, "status": ai.status} for ai in meeting.action_items],
            "decisions": [{"id": d.id, "decision_text": d.decision_text} for d in meeting.decisions],
            "topics": [{"id": t.id, "topic_text": t.topic_text} for t in meeting.topics]
        }
    finally:
        session.close()


