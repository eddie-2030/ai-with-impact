from typing import List, Dict
from ..services.ontology import ONTOLOGY


def run(extracted_edges: List[Dict]) -> List[Dict]:
    skills_by_label = {skill["canonical_label"].casefold(): skill for skill in ONTOLOGY.skills}
    normalized = []
    seen = set()
    for edge in extracted_edges:
        label = edge["label"]
        skill = skills_by_label.get(label.casefold())
        if skill is None:
            nearest = ONTOLOGY.nearest(label, top_k=1)
            if not nearest:
                continue
            skill = skills_by_label[nearest[0][0].casefold()]
        skill_id = skill["skill_id"]
        if skill_id not in seen:
            normalized.append({**edge, "skill_id": skill_id, "label": skill["canonical_label"]})
            seen.add(skill_id)
    return normalized
