from typing import List, Dict
import numpy as np
from ..services.graph_store import GRAPH
from ..services.utils import embed_texts

def _avg_emb(labels: List[str]) -> np.ndarray:
    if not labels:
        return embed_texts([""])[0]
    vecs = embed_texts(labels)
    v = vecs.mean(axis=0)
    return v / (np.linalg.norm(v)+1e-12)

def _role_vec(role_id: str) -> np.ndarray:
    reqs = GRAPH.get_role_requirements(role_id)
    labels = [r["label"] for r in reqs]
    return _avg_emb(labels)

def _person_vec(person_id: str) -> np.ndarray:
    skills = GRAPH.get_person_skills(person_id)
    labels = [s["label"] for s in skills]
    return _avg_emb(labels)

def compute_matches(person_id: str, role_catalog: List[Dict], top_k: int = 5) -> List[Dict]:
    p = _person_vec(person_id)
    out = []
    for r in role_catalog:
        rv = _role_vec(r["role_id"])
        score = float(np.dot(p, rv))
        out.append({"role_id": r["role_id"], "title": r.get("title","role"), "level": r.get("level"), "score": score})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top_k]

def compute_gap_vector(person_id: str, role_id: str) -> List[Dict]:
    have = {s["label"] for s in GRAPH.get_person_skills(person_id)}
    reqs = GRAPH.get_role_requirements(role_id)
    gaps = []
    for r in reqs:
        if r["label"] not in have:
            gaps.append({"skill": r["label"], "weight": r.get("weight",0.5), "must_have": r.get("must_have", False)})
    gaps.sort(key=lambda x: (not x["must_have"], -x["weight"]))  # must-have first
    return gaps
