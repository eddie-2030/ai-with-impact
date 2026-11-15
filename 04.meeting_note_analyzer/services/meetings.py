"""Shared meeting analysis and persistence for HTTP and batch entry points."""
from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from db.db import (
    FollowUp, Meeting, insert_action_item, insert_decision,
    insert_participant_contribution, insert_topic, session_scope,
)
from models.meeting_analyzer import analyze_meeting


DatabaseText = Annotated[str, StringConstraints(pattern=r"^[^\x00]*$")]


class MeetingInput(BaseModel):
    meeting_id: Annotated[DatabaseText, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    title: DatabaseText | None = None
    date: datetime | None = None
    participants: list[DatabaseText] = Field(default_factory=list)
    transcript: Annotated[DatabaseText, StringConstraints(strip_whitespace=True, min_length=10)]

    @field_validator("date")
    @classmethod
    def normalize_date(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            try:
                return value.astimezone(UTC).replace(tzinfo=None)
            except OverflowError:
                raise ValueError("Meeting date is outside the supported UTC range") from None
        return value


class MeetingConflict(Exception):
    """An existing meeting ID belongs to a different input."""


def _result(meeting: Meeting) -> dict:
    return {
        "meeting_id": meeting.meeting_ext_id,
        "title": meeting.title,
        "date": meeting.date.isoformat() if meeting.date else None,
        "participants": meeting.participants or [],
        "summary": meeting.summary,
        "action_items": [{
            "id": row.id, "description": row.description, "assignee": row.assignee,
            "status": row.status, "priority": row.priority,
            "due_date": row.due_date.isoformat() if row.due_date else None,
        } for row in sorted(meeting.action_items, key=lambda row: row.id)],
        "decisions": [{
            "id": row.id, "decision_text": row.decision_text, "rationale": row.rationale,
            "decision_maker": row.decision_maker,
        } for row in sorted(meeting.decisions, key=lambda row: row.id)],
        "topics": [{
            "id": row.id, "topic_text": row.topic_text, "relevance_score": row.relevance_score,
        } for row in sorted(meeting.topics, key=lambda row: row.id)],
        "follow_ups": [{
            "item": row.item, "reason": row.reason, "suggested_timeline": row.suggested_timeline,
        } for row in meeting.follow_ups],
    }


def _lookup(session: Session, meeting_id: str) -> Meeting | None:
    return session.scalar(select(Meeting).where(Meeting.meeting_ext_id == meeting_id))


def get_saved_meeting(meeting_id: str) -> dict | None:
    with session_scope() as session:
        meeting = _lookup(session, meeting_id)
        return _result(meeting) if meeting is not None else None


def _reuse(meeting: Meeting, incoming: MeetingInput) -> dict:
    if (
        meeting.title != incoming.title
        or meeting.date != incoming.date
        or (meeting.participants or []) != incoming.participants
        or (meeting.transcript or "").strip() != incoming.transcript
    ):
        raise MeetingConflict("This meeting ID already belongs to different input. Use a new meeting ID.")
    if not meeting.summary or meeting.summary.startswith("Error analyzing meeting:"):
        raise MeetingConflict("This meeting ID has a legacy incomplete analysis. Use a new meeting ID.")
    return _result(meeting)


def analyze_and_save(incoming: MeetingInput) -> dict:
    with session_scope() as session:
        meeting = _lookup(session, incoming.meeting_id)
        if meeting is not None:
            return _reuse(meeting, incoming)

    analysis = analyze_meeting(
        transcript=incoming.transcript, participants=incoming.participants, title=incoming.title,
    )

    # The unique ID arbitrates concurrent first requests. Each reader sees only committed results.
    with session_scope() as session:
        meeting_id = session.scalar(
            insert(Meeting)
            .values(
                meeting_ext_id=incoming.meeting_id, title=incoming.title, date=incoming.date,
                participants=incoming.participants, transcript=incoming.transcript,
                summary=analysis["summary"],
            )
            .on_conflict_do_nothing(index_elements=[Meeting.meeting_ext_id])
            .returning(Meeting.id)
        )
        if meeting_id is None:
            existing = _lookup(session, incoming.meeting_id)
            if existing is None:
                raise MeetingConflict("The meeting changed while saving. Retry your request.")
            return _reuse(existing, incoming)

        for item in analysis["action_items"]:
            due_date = date.fromisoformat(item["due_date"]) if item.get("due_date") else None
            insert_action_item(session, {**item, "meeting_id": meeting_id, "due_date": due_date})
        for decision in analysis["decisions"]:
            insert_decision(session, {**decision, "meeting_id": meeting_id})
        for topic in analysis["topics"]:
            insert_topic(session, {**topic, "meeting_id": meeting_id})
        for name, contribution in analysis["participant_contributions"].items():
            insert_participant_contribution(
                session, {**contribution, "meeting_id": meeting_id, "participant_name": name},
            )
        session.add_all(FollowUp(meeting_id=meeting_id, **item) for item in analysis["follow_ups"])
        session.flush()
        return _result(session.get(Meeting, meeting_id))
