from typing import List, Dict
import json, re
from ..services.utils import llm_complete
from ..services.graph_store import GRAPH
from ..services.ontology import ONTOLOGY
from ..services.rag import retrieve

PROMPT = '''You are a precise skill extraction assistant.
Given employee evidence text, extract skills ONLY from this canonical list and return a JSON array of skills.
If a phrase is close to a canonical skill, output the canonical skill exactly.

Canonical skills:
{skills}

Evidence:
{evidence}

Return ONLY a JSON array, e.g. ["python","sql"].'''

def run(person_id: str, evidence_texts: List[str]) -> List[Dict]:
    ONTOLOGY.load()
    _ = retrieve(" ".join(evidence_texts), top_k=3)
    prompt = PROMPT.format(skills=", ".join(ONTOLOGY.labels), evidence="\n".join(evidence_texts)[:8000])
    raw = llm_complete(prompt, system="You extract standardized skills and output strict JSON arrays.")
    try:
        arr = json.loads(raw)
        if not isinstance(arr, list):
            arr = []
    except Exception:
        # fallback: simple token scan
        toks = set(re.findall(r"[A-Za-z0-9_\-]+", raw.lower()))
        arr = [t for t in toks if t in (s.lower() for s in ONTOLOGY.labels)]

    edges = []
    for s in arr:
        canon = s.strip().lower()
        if canon not in (lbl.lower() for lbl in ONTOLOGY.labels):
            canon = ONTOLOGY.nearest(canon, top_k=1)[0][0]
        GRAPH.upsert_skill(canon, canonical_label=canon, taxonomy_source="ontology")
        GRAPH.add_person_skill(person_id, canon, proficiency=0.6, confidence=0.8, provenance="parser_llm_v1")
        edges.append({"skill_id": canon, "label": canon, "proficiency": 0.6, "confidence": 0.8})
    return edges
