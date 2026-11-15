"""Send one bundled synthetic profile to the running API."""

import argparse
import json
from pathlib import Path

import requests

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("person_id", help="ID from the synthetic roster, for example p100")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    with (SAMPLES / "people.jsonl").open(encoding="utf-8") as roster:
        for line in roster:
            profile = json.loads(line)
            if profile["person_id"] == args.person_id:
                break
        else:
            parser.error(f"Unknown synthetic person ID: {args.person_id}")

    evidence = []
    for directory, suffix, source in (
        ("projects", "proj", "project"),
        ("resumes", "resume", "resume"),
    ):
        path = SAMPLES / directory / f"{args.person_id}_{suffix}.txt"
        if path.is_file():
            evidence.append({"text": path.read_text(encoding="utf-8"), "source": source})
    if not evidence:
        parser.error(f"No bundled evidence for {args.person_id}")

    try:
        response = requests.post(
            f"{args.api_url.rstrip('/')}/ingest/profile",
            json={"profile": profile, "evidence": evidence},
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        parser.exit(1, f"Ingest failed: {exc}\n")
    print(f"Ingested {args.person_id}: {len(response.json()['skills_added'])} skills.")

if __name__ == "__main__":
    main()
