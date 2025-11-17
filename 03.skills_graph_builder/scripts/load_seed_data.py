import os, json
from src.orchestrator.graph import ingest_profile
from src.services.rag import index_document

BASE = "data/samples"

def _read(path):
    return open(path).read() if os.path.exists(path) else ""

def main():
    people_path = os.path.join(BASE,"people.jsonl")
    if not os.path.exists(people_path):
        print("No people.jsonl; run scripts/generate_synth_data.py first.")
        return
    with open(people_path) as f:
        for line in f:
            j = json.loads(line)
            pid = j["person_id"]
            proj = _read(os.path.join(BASE,"projects", f"{pid}_proj.txt"))
            resu = _read(os.path.join(BASE,"resumes", f"{pid}_resume.txt"))
            evidence = [t for t in [proj, resu] if t]
            for tag, txt in [("project",proj),("resume",resu)]:
                if txt:
                    index_document(f"{pid}_{tag}", txt, {"type":tag,"person_id":pid})
            ingest_profile(j, evidence)
            print(f"Ingested {pid} ({j.get('name','')}) with {len(evidence)} docs.")
    print("Seed ingestion done.")

if __name__ == "__main__":
    main()
