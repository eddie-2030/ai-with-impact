from typing import List, Dict
from ..services.graph_store import GRAPH
from ..services.rag import index_document
from ..agents import profile_parser, taxonomy_mapper, role_profiler, gap_coach, roi_estimator

def ingest_profile(person: Dict, evidence_texts: List[str]) -> List[Dict]:
    person_id = person["person_id"]
    person_data = {k: v for k, v in person.items() if k != "person_id"}
    GRAPH.upsert_person(person_id, **person_data)
    for i, t in enumerate(evidence_texts):
        index_document(f"{person['person_id']}_e_{i}", t, {"person_id": person["person_id"], "type": "evidence"})
    edges = profile_parser.run(person["person_id"], evidence_texts)
    normalized = taxonomy_mapper.run(person["person_id"], edges)
    return normalized

def recommend_roles(person_id: str, role_catalog: List[Dict], top_k: int = 5) -> List[Dict]:
    return role_profiler.compute_matches(person_id, role_catalog, top_k=top_k)

def plan_gap_actions(person_id: str, role_id: str) -> Dict:
    gaps = role_profiler.compute_gap_vector(person_id, role_id)
    plan = gap_coach.run(person_id, role_id, gaps)
    roi_estimator.log_assignment(person_id, role_id, len(plan.get("actions", [])))
    return {"gaps": gaps, **plan}
