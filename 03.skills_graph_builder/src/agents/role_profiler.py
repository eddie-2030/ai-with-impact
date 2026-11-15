from typing import List, Dict
import numpy as np
from ..services.graph_store import GRAPH
from ..services.utils import embed_texts

def _centroid(labels: List[str], embeddings: Dict[str, np.ndarray]) -> np.ndarray:
    vector = np.mean([embeddings[label] for label in labels], axis=0)
    return vector / (np.linalg.norm(vector) + 1e-12)

def compute_matches(person_id: str, role_catalog: List[Dict], top_k: int = 5) -> List[Dict]:
    person_labels = [skill["label"] for skill in GRAPH.get_person_skills(person_id) if skill["label"].strip()]
    if not person_labels:
        return []

    role_labels = []
    for role in role_catalog:
        requirements = GRAPH.get_role_requirements(role["role_id"])
        labels = [skill["label"] for skill in requirements if skill["label"].strip()]
        if labels:
            role_labels.append((role, labels))
    if not role_labels:
        return []

    labels = list(dict.fromkeys(person_labels + [label for _, skills in role_labels for label in skills]))
    embeddings = dict(zip(labels, embed_texts(labels), strict=True))
    person_vector = _centroid(person_labels, embeddings)
    out = []
    for role, skills in role_labels:
        score = float(np.dot(person_vector, _centroid(skills, embeddings)))
        out.append({"role_id": role["role_id"], "title": role.get("title", "role"), "level": role.get("level"), "score": score})
    out.sort(key=lambda match: (-match["score"], match["role_id"]))
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
