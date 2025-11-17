from fastapi import FastAPI, HTTPException
from typing import List
import os, csv
from .services.schemas import IngestProfileRequest, RoleMatch, HealthResponse
from .services.graph_store import GRAPH
from .orchestrator.graph import ingest_profile, recommend_roles, plan_gap_actions

app = FastAPI(title="Skills Graph Builder & Gap-to-Role Coach (LLM)", version="1.0.0")

ROLE_CATALOG_PATH = os.getenv("ROLE_CATALOG_CSV", "data/roles/role_skill_requirements.csv" )

def _read_roles():
    roles = {}
    if not os.path.exists(ROLE_CATALOG_PATH): return []
    with open(ROLE_CATALOG_PATH) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rid = r["role_id"]
            if rid not in roles:
                roles[rid] = {"role_id": rid, "title": r.get("title","role"), "level": r.get("level",""), "skills": []}
            roles[rid]["skills"].append({"skill_id": r["skill_id"], "label": r["skill_label"], "weight": float(r.get("weight",0.5)), "must_have": r.get("must_have","false").lower()=="true"})
    for rid, role in roles.items():
        GRAPH.upsert_role(rid, title=role["title"], level=role["level"])
        for s in role["skills"]:
            GRAPH.upsert_skill(s["skill_id"], canonical_label=s["label"], taxonomy_source="seed")
            GRAPH.add_role_skill(rid, s["skill_id"], weight=s["weight"], must_have=s["must_have"])
    return list(roles.values())

ROLE_CATALOG = _read_roles()

def _load_people_data():
    """Load people data from the generated files"""
    import json
    BASE = "data/samples"
    people_path = os.path.join(BASE, "people.jsonl")
    
    if not os.path.exists(people_path):
        print("No people.jsonl found; run scripts/generate_synth_data.py first.")
        return
    
    with open(people_path) as f:
        for line in f:
            j = json.loads(line)
            pid = j["person_id"]
            proj_path = os.path.join(BASE, "projects", f"{pid}_proj.txt")
            resu_path = os.path.join(BASE, "resumes", f"{pid}_resume.txt")
            
            proj = open(proj_path).read() if os.path.exists(proj_path) else ""
            resu = open(resu_path).read() if os.path.exists(resu_path) else ""
            evidence = [t for t in [proj, resu] if t]
            
            # Ingest the profile
            ingest_profile(j, evidence)
            print(f"Loaded {pid} ({j.get('name','')}) with {len(evidence)} docs.")

# Load people data on startup
_load_people_data()

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()

@app.get("/roles")
def roles():
    return ROLE_CATALOG

@app.get("/persons")
def persons():
    res = []
    for n, attrs in GRAPH.G.nodes(data=True):
        if n[0] == "person":
            res.append({"person_id": n[1], **attrs})
    return res

@app.get("/person/{person_id}/skills")
def person_skills(person_id: str):
    return GRAPH.get_person_skills(person_id)

@app.post("/ingest/profile")
def ingest(req: IngestProfileRequest):
    texts = [e.text for e in req.evidence]
    edges = ingest_profile(req.profile.model_dump(), texts)
    return {"person_id": req.profile.person_id, "skills_added": edges}

@app.get("/roles/matches", response_model=List[RoleMatch])
def matches(person_id: str, top_k: int = 5):
    if not ROLE_CATALOG: raise HTTPException(500, "Role catalog is empty")
    return recommend_roles(person_id, ROLE_CATALOG, top_k=top_k)

@app.get("/recommendations/{person_id}")
def recommend(person_id: str, role_id: str = None):
    if not role_id:
        best = recommend_roles(person_id, ROLE_CATALOG, top_k=1)
        if not best: raise HTTPException(404, "No role matches found for this person")
        role_id = best[0]["role_id"]
    plan = plan_gap_actions(person_id, role_id)
    return {"person_id": person_id, "role_id": role_id, **plan}
