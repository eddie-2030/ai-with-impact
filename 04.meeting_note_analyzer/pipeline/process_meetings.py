"""Analyze the JSON meeting records in INPUT_DIR."""
import json
import os
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from db.db import init_db
from models.meeting_analyzer import AnalysisUnavailable, InvalidAnalysis
from services.meetings import MeetingConflict, MeetingInput, analyze_and_save


def process_one(record: dict) -> dict | None:
    try:
        meeting = MeetingInput.model_validate(record)
    except ValidationError:
        print("Error processing meeting: invalid input")
        return None

    try:
        result = analyze_and_save(meeting)
    except (MeetingConflict, AnalysisUnavailable, InvalidAnalysis) as error:
        print(f"Error processing {meeting.meeting_id}: {error}")
        return None
    except SQLAlchemyError:
        print(f"Error processing {meeting.meeting_id}: failed to save analysis")
        return None

    counts = {
        key: len(result[key]) for key in ("action_items", "decisions", "topics", "follow_ups")
    }
    print(
        f"Processed {meeting.meeting_id}: {counts['action_items']} action items, "
        f"{counts['decisions']} decisions, {counts['topics']} topics, {counts['follow_ups']} follow-ups"
    )
    return {"meeting_id": meeting.meeting_id, **counts}


def main() -> int:
    directory = Path(os.getenv("INPUT_DIR", "./data/meetings"))
    if not directory.is_dir():
        print("Input directory does not exist")
        return 1
    if not (files := sorted(directory.glob("*.json"))):
        print("No JSON meeting files found")
        return 0

    init_db()
    failures = 0
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            print(f"Error reading {path.name}: expected a JSON file")
            failures += 1
            continue
        if process_one(record) is None:
            failures += 1
    print(f"Batch finished: {len(files) - failures} succeeded, {failures} failed")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())

