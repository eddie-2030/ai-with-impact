# models/meeting_analyzer.py
from __future__ import annotations
import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

PROMPT_TEMPLATE = """Analyze the following meeting transcript and extract structured information.

Meeting Participants: {participants}
Meeting Title: {title}

Transcript:
{transcript}

Please extract and return a JSON object with the following structure:
{{
  "summary": "A concise 2-3 sentence summary of the meeting",
  "action_items": [
    {{
      "description": "Action item description",
      "assignee": "Person responsible (or null if not specified)",
      "due_date": "YYYY-MM-DD or null if not specified",
      "priority": "low, medium, or high"
    }}
  ],
  "decisions": [
    {{
      "decision_text": "What was decided",
      "rationale": "Why this decision was made (or null)",
      "decision_maker": "Who made the decision (or null)"
    }}
  ],
  "topics": [
    {{
      "topic_text": "Main topic discussed",
      "relevance_score": 0.0-1.0
    }}
  ],
  "participant_contributions": {{
    "participant_name": {{
      "contribution_count": number of times they spoke,
      "word_count": approximate word count
    }}
  }}
}}

Return ONLY valid JSON, no additional text."""

def analyze_meeting(transcript: str, participants: List[str], title: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a meeting transcript and extract structured information"""
    
    participants_str = ", ".join(participants) if participants else "Unknown"
    title_str = title or "Meeting"
    
    prompt = PROMPT_TEMPLATE.format(
        participants=participants_str,
        title=title_str,
        transcript=transcript
    )
    
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a meeting analysis assistant. You extract structured information from meeting transcripts. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        response_text = completion.choices[0].message.content
        result = json.loads(response_text)
        
        # Ensure all required fields exist
        result.setdefault("summary", "")
        result.setdefault("action_items", [])
        result.setdefault("decisions", [])
        result.setdefault("topics", [])
        result.setdefault("participant_contributions", {})
        
        return result
        
    except Exception as e:
        # Fallback response on error
        return {
            "summary": f"Error analyzing meeting: {str(e)}",
            "action_items": [],
            "decisions": [],
            "topics": [],
            "participant_contributions": {}
        }

def extract_follow_ups(transcript: str, participants: List[str]) -> List[Dict[str, Any]]:
    """Extract items that require follow-up meetings"""
    
    follow_up_prompt = f"""Analyze this meeting transcript and identify items that require follow-up meetings or additional discussion.

Participants: {', '.join(participants) if participants else 'Unknown'}

Transcript:
{transcript}

Return a JSON array of follow-up items:
[
  {{
    "item": "Description of what needs follow-up",
    "reason": "Why follow-up is needed",
    "suggested_timeline": "When follow-up should occur"
  }}
]

Return ONLY valid JSON array, no additional text."""
    
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You identify items requiring follow-up meetings. Return valid JSON only."},
                {"role": "user", "content": follow_up_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        response_text = completion.choices[0].message.content
        result = json.loads(response_text)
        
        # Handle both array and object with array key
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "follow_ups" in result:
            return result["follow_ups"]
        else:
            return []
            
    except Exception as e:
        return []

