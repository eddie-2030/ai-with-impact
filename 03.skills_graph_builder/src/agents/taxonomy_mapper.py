from typing import List, Dict
from ..services.graph_store import GRAPH
from ..services.ontology import ONTOLOGY

def run(person_id: str, extracted_edges: List[Dict]) -> List[Dict]:
    ONTOLOGY.load()
    normalized = []
    for e in extracted_edges:
        label = e["label"]
        nearest, sim = ONTOLOGY.nearest(label, top_k=1)[0]
        GRAPH.upsert_skill(nearest, canonical_label=nearest, taxonomy_source="ontology")
        normalized.append({**e, "skill_id": nearest, "label": nearest})
    return normalized
