from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
import json
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError


def test_out_of_range_utc_date_returns_redacted_validation_error(db, entrypoints, meeting_record):
    api, _ = entrypoints
    invalid = {**meeting_record, "date": "0001-01-01T00:00:00+23:00"}
    with TestClient(api.app) as client:
        response = client.post("/analyze", json=invalid)
    assert response.status_code == 422
    assert "outside the supported UTC range" in response.text
    assert invalid["date"] not in response.text
    assert invalid["transcript"] not in response.text


def assert_linked_analysis(db, meeting_id):
    with db.SessionLocal() as session:
        meeting = session.query(db.Meeting).filter_by(meeting_ext_id=meeting_id).one()
        assert meeting.participants == ["Alice"]
        assert len(meeting.action_items) == 1
        assert len(meeting.decisions) == 1
        assert len(meeting.topics) == 1
        assert len(meeting.participant_contributions) == 1
        assert meeting.action_items[0].due_date == date(2026, 11, 6)
        contribution = meeting.participant_contributions[0]
        assert (contribution.contribution_count, contribution.word_count) == (2, 15)
        for model in (db.ActionItem, db.Decision, db.Topic, db.ParticipantContribution):
            assert session.query(model).filter(model.meeting_id.is_(None)).count() == 0


def test_helpers_return_database_ids_and_link_children_before_commit(db):
    with db.session_scope() as session:
        meeting = db.upsert_meeting(session, {"meeting_ext_id": "helpers", "title": "Initial"})
        assert isinstance(meeting.id, int)
        updated = db.upsert_meeting(session, {"meeting_ext_id": "helpers", "title": "Updated"})
        assert updated.id == meeting.id

        children = [
            db.insert_action_item(session, {"meeting_id": meeting.id, "description": "Publish"}),
            db.insert_decision(session, {"meeting_id": meeting.id, "decision_text": "Approve"}),
            db.insert_topic(session, {"meeting_id": meeting.id, "topic_text": "Roadmap"}),
            db.insert_participant_contribution(session, {
                "meeting_id": meeting.id, "participant_name": "Alice",
                "contribution_count": 2, "word_count": 15,
            }),
        ]
        assert all(isinstance(child.id, int) for child in children)
        assert all(child.meeting_id == meeting.id for child in children)
        assert children[0].status == "open"
        assert children[0].priority == "medium"

        contribution = db.insert_participant_contribution(session, {
            "meeting_id": meeting.id, "participant_name": "Alice",
            "contribution_count": 1, "word_count": 5,
        })
        assert contribution.id == children[-1].id
        assert (contribution.contribution_count, contribution.word_count) == (3, 20)

    with db.SessionLocal() as session:
        meeting = session.query(db.Meeting).one()
        assert meeting.title == "Updated"
        assert len(meeting.action_items) == len(meeting.decisions) == len(meeting.topics) == 1
        assert len(meeting.participant_contributions) == 1


@pytest.mark.parametrize("existing", [False, True], ids=["new-meeting", "existing-meeting"])
def test_flushed_writes_remain_in_the_enclosing_transaction(db, existing):
    if existing:
        with db.session_scope() as session:
            db.upsert_meeting(session, {"meeting_ext_id": "rollback", "title": "Original"})

    with pytest.raises(IntegrityError):
        with db.session_scope() as session:
            meeting = db.upsert_meeting(session, {"meeting_ext_id": "rollback", "title": "Changed"})
            db.insert_action_item(session, {"meeting_id": meeting.id, "description": "Publish"})
            # A later database failure must undo the parent and earlier children.
            db.insert_decision(session, {"meeting_id": meeting.id, "decision_text": None})

    with db.SessionLocal() as session:
        assert session.query(db.ActionItem).count() == 0
        assert session.query(db.Decision).count() == 0
        meeting = session.query(db.Meeting).one_or_none()
        if existing:
            assert meeting.title == "Original"
        else:
            assert meeting is None


def test_analyze_returns_ids_that_match_the_saved_meeting(db, entrypoints, meeting_record, analysis, follow_ups):
    api, _ = entrypoints
    with TestClient(api.app) as client:
        response = client.post("/analyze", json=meeting_record)
        assert response.status_code == 200
        posted = response.json()
        assert posted["summary"] == analysis["summary"]
        assert posted["follow_ups"] == follow_ups
        for collection in ("action_items", "decisions", "topics"):
            assert len(posted[collection]) == 1
            assert isinstance(posted[collection][0]["id"], int)

        response = client.get(f"/meetings/{meeting_record['meeting_id']}")
        assert response.status_code == 200
        saved = response.json()
        for collection in ("action_items", "decisions", "topics"):
            assert [item["id"] for item in saved[collection]] == [item["id"] for item in posted[collection]]
        assert saved["summary"] == posted["summary"]
    assert_linked_analysis(db, meeting_record["meeting_id"])


def test_batch_processing_persists_linked_analysis(db, entrypoints, meeting_record, capsys):
    _, pipeline = entrypoints
    result = pipeline.process_one(meeting_record)
    assert result == {
        "meeting_id": meeting_record["meeting_id"],
        "action_items": 1, "decisions": 1, "topics": 1, "follow_ups": 1,
    }
    assert "Processed roadmap-planning" in capsys.readouterr().out
    assert_linked_analysis(db, meeting_record["meeting_id"])


def test_batch_failure_rolls_back_earlier_writes(db, entrypoints, meeting_record, analysis, capsys):
    _, pipeline = entrypoints
    analysis["decisions"][0]["decision_text"] = None
    assert pipeline.process_one(meeting_record) is None
    assert "Error processing roadmap-planning" in capsys.readouterr().out
    with db.SessionLocal() as session:
        for model in (db.Meeting, db.ActionItem, db.Decision, db.Topic, db.ParticipantContribution):
            assert session.query(model).count() == 0


def test_repeat_submission_is_shared_by_api_and_batch(
    db, entrypoints, meeting_record, follow_ups, analysis_provider
):
    api, pipeline = entrypoints
    with TestClient(api.app) as client:
        original = client.post("/analyze", json=meeting_record)
        assert original.status_code == 200, original.text
        assert pipeline.process_one(meeting_record)["follow_ups"] == 1
        replay = client.post("/analyze", json=meeting_record)
        assert replay.status_code == 200, replay.text
        assert replay.json() == original.json()
        saved = client.get(f"/meetings/{meeting_record['meeting_id']}")
        assert saved.status_code == 200, saved.text
        assert saved.json()["follow_ups"] == follow_ups
    analysis_provider.assert_called_once()
    assert_linked_analysis(db, meeting_record["meeting_id"])


def test_same_id_with_changed_content_does_not_overwrite(
    db, entrypoints, meeting_record, analysis_provider
):
    api, pipeline = entrypoints
    changed = {**meeting_record, "transcript": "Alice: Here is a different transcript."}
    with TestClient(api.app) as client:
        original = client.post("/analyze", json=meeting_record)
        assert original.status_code == 200, original.text
        conflict = client.post("/analyze", json=changed)
        assert conflict.status_code == 409, conflict.text
        assert pipeline.process_one(changed) is None
        replay = client.post("/analyze", json=meeting_record)
        assert replay.status_code == 200, replay.text
        assert replay.json() == original.json()
    analysis_provider.assert_called_once()
    assert_linked_analysis(db, meeting_record["meeting_id"])


def test_concurrent_identical_first_submissions_share_saved_result(
    db, entrypoints, meeting_record, analysis_provider
):
    api, _ = entrypoints
    both_analyzing = Barrier(2, timeout=10)
    fixture = analysis_provider.side_effect

    def simultaneous_analysis(**kwargs):
        both_analyzing.wait()
        return fixture(**kwargs)

    analysis_provider.side_effect = simultaneous_analysis
    with TestClient(api.app) as client, ThreadPoolExecutor(max_workers=2) as callers:
        def submit():
            return client.post("/analyze", json=meeting_record)

        first = callers.submit(submit)
        second = callers.submit(submit)
        responses = [response.result(timeout=15) for response in (first, second)]
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert analysis_provider.call_count == 2
    assert_linked_analysis(db, meeting_record["meeting_id"])


def test_legacy_record_is_readable_and_reused_without_follow_ups(
    db, entrypoints, meeting_record, analysis_provider
):
    api, _ = entrypoints
    # Simulate a database created before follow-ups were persisted.
    db.FollowUp.__table__.drop(db.engine)
    with db.session_scope() as session:
        meeting = db.upsert_meeting(session, {
            "meeting_ext_id": meeting_record["meeting_id"],
            "title": meeting_record["title"],
            "date": datetime.fromisoformat(meeting_record["date"]),
            "participants": meeting_record["participants"],
            "transcript": meeting_record["transcript"],
            "summary": "Legacy summary",
        })
        item = db.insert_action_item(session, {"meeting_id": meeting.id, "description": "Preserved"})
        item_id = item.id
    with TestClient(api.app) as client:
        saved = client.get(f"/meetings/{meeting_record['meeting_id']}")
        assert saved.status_code == 200, saved.text
        assert saved.json()["follow_ups"] == []
        replay = client.post("/analyze", json=meeting_record)
        assert replay.status_code == 200, replay.text
        assert replay.json()["summary"] == "Legacy summary"
        assert replay.json()["action_items"][0]["id"] == item_id
    analysis_provider.assert_not_called()


@pytest.mark.parametrize(
    "error_type, status", [("AnalysisUnavailable", 503), ("InvalidAnalysis", 502)]
)
def test_model_failure_does_not_persist_partial_analysis(
    db, entrypoints, meeting_record, analysis_provider, error_type, status
):
    from models import meeting_analyzer

    api, _ = entrypoints
    analysis_provider.side_effect = getattr(meeting_analyzer, error_type)("Model unavailable")
    with TestClient(api.app) as client:
        response = client.post("/analyze", json=meeting_record)
        assert response.status_code == status, response.text
        assert client.get(f"/meetings/{meeting_record['meeting_id']}").status_code == 404
    with db.SessionLocal() as session:
        for model in (db.Meeting, db.ActionItem, db.Decision, db.Topic, db.ParticipantContribution):
            assert session.query(model).count() == 0


def test_batch_reports_file_failure_and_processes_other_records(
    db, entrypoints, meeting_record, tmp_path, monkeypatch
):
    _, pipeline = entrypoints
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    (tmp_path / "good.json").write_text(json.dumps(meeting_record), encoding="utf-8")
    monkeypatch.setenv("INPUT_DIR", str(tmp_path))
    assert pipeline.main() == 1
    assert_linked_analysis(db, meeting_record["meeting_id"])
