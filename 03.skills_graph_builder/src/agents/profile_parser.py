import json
from typing import Dict, List

from ..services.utils import ProviderUnavailable, llm_complete
from ..services.ontology import ONTOLOGY

PROMPT = '''You are a precise skill extraction assistant.
Given employee evidence text, extract skills ONLY from this canonical list and return a JSON array of skills.
If a phrase is close to a canonical skill, output the canonical skill exactly.

Canonical skills:
{skills}

Evidence:
{evidence}

Return ONLY a JSON array, e.g. ["python","sql"].'''

def run(evidence_texts: List[str]) -> List[Dict]:
    if not evidence_texts:
        return []
    if not ONTOLOGY.labels:
        ONTOLOGY.load()
    prompt = PROMPT.format(skills=", ".join(ONTOLOGY.labels), evidence="\n".join(evidence_texts)[:8000])
    raw = llm_complete(prompt, system="You extract standardized skills and output strict JSON arrays.")
    try:
        arr = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProviderUnavailable("provider_invalid_response", "The provider returned invalid skill data.") from error
    if not isinstance(arr, list) or not all(isinstance(label, str) for label in arr):
        raise ProviderUnavailable("provider_invalid_response", "The provider returned invalid skill data.")
    return [
        {"label": label.strip(), "proficiency": 0.6, "confidence": 0.8}
        for label in arr
        if label.strip()
    ]
