import os, json, random
BASE = "data/samples"
os.makedirs(BASE, exist_ok=True)
os.makedirs(os.path.join(BASE,"projects"), exist_ok=True)
os.makedirs(os.path.join(BASE,"resumes"), exist_ok=True)

N = 50
FIRST = ["Alex","Taylor","Jordan","Riley","Casey","Sam","Quinn","Morgan","Hayden","Avery","Jamie","Reese","Skyler","Parker","Drew"]
LAST = ["Lee","Chen","Singh","Garcia","Martinez","Nguyen","Wang","Patel","Kim","Davis","Hernandez","Lopez","Brown","Wilson","Clark"]
LOCS = ["NYC","Seattle","Austin","Remote","London","Toronto"]
ORG = ["Analytics","Platform","Data Science","Customer","Ops"]

skills = ["python","sql","pandas","numpy","scikit-learn","mlops","llmops","retrieval","rag","prompt-engineering","fastapi","neo4j","pgvector","langchain","langgraph","aws","gcp","azure","etl","airflow","docker"]

def make_person(i):
    import random
    name = f"{random.choice(FIRST)} {random.choice(LAST)}"
    role = random.choice(["BI Analyst","Data Engineer","Data Analyst","ML Engineer","Platform Analyst"])
    loc = random.choice(LOCS)
    org = random.choice(ORG)
    pid = f"p{100+i}"
    return {"person_id": pid, "name": name, "org_unit": org, "location": loc, "role_current": role}

def skill_sentence(s):
    return f"Hands-on experience with {s} in real projects."

def make_project_text(skillset):
    lines = [
        "Collaborated across functions to deliver quarterly outcomes.",
        "Reduced manual toil with automation and templates."
    ]
    lines += [skill_sentence(s) for s in skillset]
    return "\n".join(lines)

def make_resume_text(skillset):
    bullets = [f"- Built features leveraging {s}." for s in skillset]
    bullets += ["- Presented insights to executives.", "- Mentored junior analysts."]
    return "\n".join(bullets)

with open(os.path.join(BASE, "people.jsonl"), "w") as f:
    for i in range(N):
        person = make_person(i)
        f.write(json.dumps(person) + "\n")
        person_skills = random.sample(skills, k=random.randint(3,7))
        with open(os.path.join(BASE, "projects", f"{person['person_id']}_proj.txt"), "w") as pf:
            pf.write(make_project_text(person_skills))
        with open(os.path.join(BASE, "resumes", f"{person['person_id']}_resume.txt"), "w") as rf:
            rf.write(make_resume_text(person_skills))
print(f"Wrote {N} synthetic people + docs.")
