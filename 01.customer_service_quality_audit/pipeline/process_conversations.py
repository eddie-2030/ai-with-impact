# pipeline/process_conversations.py
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict
from db.db import session_scope, init_db, upsert_agent, insert_conversation, insert_score
from ingest.anonymize import anonymize
from models.llm_scorer import score_conversation

INPUT_DIR = os.getenv("INPUT_DIR", "./data/conversations/")

def process_one(record: Dict):
    with session_scope() as s:
        agent = upsert_agent(s, agent_ext_id=record.get("agent_id", "unknown"), name=record.get("agent_name"))
        red_text, _ = anonymize(record["transcript"])
        conv = insert_conversation(s, {
            "conv_ext_id": record["conversation_id"],
            "agent_id": agent.id,
            "started_at": datetime.fromisoformat(record.get("started_at")) if record.get("started_at") else None,
            "channel": record.get("channel", "chat"),
            "language": record.get("language", "en"),
            "raw_text": record["transcript"],
            "redacted_text": red_text,
        })
        scored = score_conversation(red_text)
        insert_score(s, {
            "conversation_id": conv.id,
            "model_version": scored.get("model_version", "heuristic-v1"),
            "professionalism": scored["professionalism"],
            "friendliness": scored["friendliness"],
            "resolution_effectiveness": scored["resolution_effectiveness"],
            "explanation": scored["explanation"],
        })

def main():
    init_db()
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    for f in files:
        path = os.path.join(INPUT_DIR, f)
        with open(path, 'r') as fp:
            rec = json.load(fp)
        process_one(rec)
        print(f"Processed {f}")

if __name__ == "__main__":
    main()
