# pipeline/process_meetings.py
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, date
from typing import Dict
from db.db import session_scope, init_db, upsert_meeting, insert_action_item, insert_decision, insert_topic, insert_participant_contribution
from models.meeting_analyzer import analyze_meeting, extract_follow_ups

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INPUT_DIR = os.getenv("INPUT_DIR", "./data/meetings/")

def process_one(record: Dict):
    """Process a single meeting record"""
    try:
        # Analyze meeting using LLM
        analysis = analyze_meeting(
            transcript=record.get("transcript", ""),
            participants=record.get("participants", []),
            title=record.get("title")
        )
        
        # Extract follow-ups
        follow_ups = extract_follow_ups(record.get("transcript", ""), record.get("participants", []))
        
        # Parse meeting date
        meeting_date = None
        if record.get("date"):
            try:
                meeting_date = datetime.fromisoformat(record["date"].replace('Z', '+00:00'))
            except:
                pass
        
        # Store in database
        with session_scope() as s:
            db_meeting = upsert_meeting(s, {
                "meeting_ext_id": record.get("meeting_id", "unknown"),
                "title": record.get("title"),
                "date": meeting_date,
                "participants": record.get("participants", []),
                "transcript": record.get("transcript", ""),
                "summary": analysis.get("summary", "")
            })
            
            # Store action items
            action_item_count = 0
            for ai in analysis.get("action_items", []):
                due_date = None
                if ai.get("due_date"):
                    try:
                        due_date = datetime.fromisoformat(ai["due_date"]).date()
                    except:
                        pass
                
                insert_action_item(s, {
                    "meeting_id": db_meeting.id,
                    "description": ai.get("description", ""),
                    "assignee": ai.get("assignee"),
                    "due_date": due_date,
                    "priority": ai.get("priority", "medium"),
                    "status": "open"
                })
                action_item_count += 1
            
            # Store decisions
            decision_count = 0
            for dec in analysis.get("decisions", []):
                insert_decision(s, {
                    "meeting_id": db_meeting.id,
                    "decision_text": dec.get("decision_text", ""),
                    "rationale": dec.get("rationale"),
                    "decision_maker": dec.get("decision_maker")
                })
                decision_count += 1
            
            # Store topics
            topic_count = 0
            for topic in analysis.get("topics", []):
                insert_topic(s, {
                    "meeting_id": db_meeting.id,
                    "topic_text": topic.get("topic_text", ""),
                    "relevance_score": topic.get("relevance_score")
                })
                topic_count += 1
            
            # Store participant contributions
            for participant, contrib in analysis.get("participant_contributions", {}).items():
                insert_participant_contribution(s, {
                    "meeting_id": db_meeting.id,
                    "participant_name": participant,
                    "contribution_count": contrib.get("contribution_count", 0),
                    "word_count": contrib.get("word_count", 0)
                })
        
        print(f"Processed {record.get('meeting_id', 'unknown')}: {action_item_count} action items, {decision_count} decisions, {topic_count} topics, {len(follow_ups)} follow-ups")
        return {
            "meeting_id": record.get("meeting_id"),
            "action_items": action_item_count,
            "decisions": decision_count,
            "topics": topic_count,
            "follow_ups": len(follow_ups)
        }
    except Exception as e:
        print(f"Error processing {record.get('meeting_id', 'unknown')}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    init_db()
    
    if not os.path.exists(INPUT_DIR):
        print(f"Input directory {INPUT_DIR} does not exist")
        return
    
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    
    if not files:
        print(f"No JSON files found in {INPUT_DIR}")
        return
    
    print(f"Found {len(files)} meeting files to process")
    
    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                record = json.load(f)
            process_one(record)
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
    print("Batch processing complete")

if __name__ == "__main__":
    main()

