# models/llm_scorer.py
from __future__ import annotations
import os
from typing import Dict, Any

BACKEND = os.getenv("LLM_BACKEND", "heuristic").lower()
MODEL_VERSION = f"{BACKEND}-v1"

# ---------- Prompt Template (used by OpenAI backend) ----------
PROMPT = (
    "You are a QA evaluator. Read the conversation and rate 3 aspects from 1 (poor) to 5 (excellent):\n"
    "1) Professionalism 2) Friendliness 3) Resolution Effectiveness.\n"
    "Return strict JSON with keys: professionalism, friendliness, resolution_effectiveness, explanation (object with 3 short strings).\n"
    "Conversation:\n"
)

# ---------- OpenAI Backend ----------
def _score_openai(transcript: str) -> Dict[str, Any]:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": PROMPT + transcript},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    data = completion.choices[0].message.content
    import json
    parsed = json.loads(data)
    # Coerce to floats
    return {
        "model_version": MODEL_VERSION,
        "professionalism": float(parsed.get("professionalism", 3)),
        "friendliness": float(parsed.get("friendliness", 3)),
        "resolution_effectiveness": float(parsed.get("resolution_effectiveness", 3)),
        "explanation": parsed.get("explanation", {}),
    }

# ---------- Heuristic Fallback (no external API) ----------
POS_WORDS = {"please", "thank", "thanks", "appreciate", "happy to", "glad"}
EMP_WORDS = {"sorry", "apologize", "understand", "frustrating", "I can imagine"}
UNPROF = {"dude", "bro", "lol", "wtf", "ain't"}
RESOLVE = {"resolved", "credit issued", "refund", "fixed", "replacement", "ticket closed", "escalated"}
PROTOCOL = {"verify", "account", "security", "policy", "steps"}

def _normalize(x: float) -> float:
    return max(1.0, min(5.0, x))

def _score_heuristic(transcript: str) -> Dict[str, Any]:
    t = transcript.lower()
    pos = sum(w in t for w in POS_WORDS)
    emp = sum(w in t for w in EMP_WORDS)
    unp = sum(w in t for w in UNPROF)
    res = sum(w in t for w in RESOLVE)
    pro = sum(w in t for w in PROTOCOL)

    professionalism = _normalize(3 + 0.3*pro - 0.6*unp)
    friendliness = _normalize(3 + 0.4*pos + 0.5*emp - 0.3*unp)
    resolution_effectiveness = _normalize(2.5 + 0.8*res + 0.2*pro)

    return {
        "model_version": MODEL_VERSION,
        "professionalism": professionalism,
        "friendliness": friendliness,
        "resolution_effectiveness": resolution_effectiveness,
        "explanation": {
            "professionalism": f"Protocol refs: {pro}, informal terms: {unp}",
            "friendliness": f"Politeness markers: {pos}, empathy markers: {emp}",
            "resolution_effectiveness": f"Resolution cues: {res}",
        },
    }

def score_conversation(transcript: str) -> Dict[str, Any]:
    if BACKEND == "openai":
        return _score_openai(transcript)
    return _score_heuristic(transcript)
