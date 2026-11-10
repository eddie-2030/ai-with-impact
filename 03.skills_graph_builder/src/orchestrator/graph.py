from typing import List, Dict
from ..services.graph_store import GRAPH
from ..services.utils import embed_texts
from ..services.vector_store import VECTOR_DB
from ..agents import profile_parser, taxonomy_mapper, role_profiler, gap_coach, roi_estimator

def ingest_profile(person: Dict, evidence_texts: List[str]) -> List[Dict]:
    person_id = person["person_id"]
    evidence_texts = [text for text in evidence_texts if text.strip()]
    edges = taxonomy_mapper.run(profile_parser.run(evidence_texts))
    embeddings = embed_texts(evidence_texts)

    # Finish all provider work before modifying the graph or evidence index.
    person_data = {k: v for k, v in person.items() if k != "person_id"}
    GRAPH.upsert_person(person_id, **person_data)
    for edge in edges:
        skill_id = edge["skill_id"]
        GRAPH.upsert_skill(skill_id, canonical_label=edge["label"], taxonomy_source="ontology")
        GRAPH.add_person_skill(
            person_id, skill_id, proficiency=edge["proficiency"],
            confidence=edge["confidence"], provenance="parser_llm_v1",
        )
    for i, embedding in enumerate(embeddings):
        VECTOR_DB.upsert_embedding(
            f"{person_id}_e_{i}", embedding, {"person_id": person_id, "type": "evidence"}
        )
    return edges

def recommend_roles(person_id: str, role_catalog: List[Dict], top_k: int = 5) -> List[Dict]:
    return role_profiler.compute_matches(person_id, role_catalog, top_k=top_k)

def plan_gap_actions(person_id: str, role_id: str) -> Dict:
    gaps = role_profiler.compute_gap_vector(person_id, role_id)
    plan = gap_coach.run(person_id, role_id, gaps)
    roi_estimator.log_assignment(person_id, role_id, len(plan.get("actions", [])))
    return {"gaps": gaps, **plan}
