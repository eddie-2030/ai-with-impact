from typing import List, Dict
import csv, os

COURSES_PATH = os.getenv("COURSES_CSV", "data/samples/courses.csv" )

def _load_courses():
    if not os.path.exists(COURSES_PATH): return []
    with open(COURSES_PATH) as f:
        return list(csv.DictReader(f))

def run(person_id: str, role_id: str, gaps: List[Dict]) -> Dict:
    courses = _load_courses()
    actions = []
    for g in gaps[:5]:
        recs = [c for c in courses if g["skill"].lower() in c["skill"].lower()]
        for r in recs[:2]:
            actions.append({"type":"course","title":r["title"],"skill":g["skill"],"url":r.get("url","#"),"est_hours":r.get("hours","4")})
    rationale = f"Targeting {len(gaps)} gaps for role {role_id}; prioritizing must-have and high-weight skills."
    return {"actions": actions[:8], "rationale": rationale}
