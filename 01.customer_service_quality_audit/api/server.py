# api/server.py
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from db.db import session_scope, init_db, upsert_agent, insert_conversation, insert_score
from ingest.anonymize import anonymize
from models.llm_scorer import score_conversation
from datetime import datetime

app = FastAPI(title="CX QA Scoring API", version="1.0")

class ConversationIn(BaseModel):
    conversation_id: str
    agent_id: str
    agent_name: Optional[str] = None
    started_at: Optional[str] = None
    channel: Optional[str] = "chat"
    language: Optional[str] = "en"
    transcript: str = Field(..., min_length=10)

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/score")
async def score(conv: ConversationIn) -> Dict[str, Any]:
    red_text, _ = anonymize(conv.transcript)
    scored = score_conversation(red_text)

    with session_scope() as s:
        agent = upsert_agent(s, agent_ext_id=conv.agent_id, name=conv.agent_name)
        c = insert_conversation(s, {
            "conv_ext_id": conv.conversation_id,
            "agent_id": agent.id,
            "started_at": datetime.fromisoformat(conv.started_at) if conv.started_at else None,
            "channel": conv.channel,
            "language": conv.language,
            "raw_text": conv.transcript,
            "redacted_text": red_text,
        })
        insert_score(s, {
            "conversation_id": c.id,
            "model_version": scored.get("model_version", "heuristic-v1"),
            "professionalism": scored["professionalism"],
            "friendliness": scored["friendliness"],
            "resolution_effectiveness": scored["resolution_effectiveness"],
            "explanation": scored["explanation"],
        })

    return {
        "conversation_id": conv.conversation_id,
        "scores": {
            "professionalism": scored["professionalism"],
            "friendliness": scored["friendliness"],
            "resolution_effectiveness": scored["resolution_effectiveness"],
        },
        "explanation": scored["explanation"],
    }
