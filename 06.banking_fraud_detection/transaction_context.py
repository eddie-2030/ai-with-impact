"""Shared UTC and event-time rules for transaction assessment.

The existing database stores timestamp-without-time-zone values. Treat legacy
naive values as UTC and normalize aware values before comparing or storing them.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union


def normalize_timestamp(value: Union[str, datetime]) -> datetime:
    """Return an aware UTC datetime or a consistent validation error."""
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime):
            raise ValueError("Expected a datetime or ISO 8601 string")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("timestamp must be a valid ISO 8601 datetime") from exc


def history_for_transaction(transaction: Dict, history: Optional[List[Dict]]) -> List[Dict]:
    """Normalize account history and exclude this transaction and future events.

    Equal-time peers are allowed; identity, rather than timestamp equality,
    distinguishes the transaction currently being assessed.
    """
    event_time = normalize_timestamp(transaction.get("timestamp"))
    result = []
    for row in history or []:
        if transaction.get("user_id") is not None and row.get("user_id") != transaction["user_id"]:
            continue
        if transaction.get("transaction_id") is not None and row.get("transaction_id") == transaction["transaction_id"]:
            continue
        timestamp = normalize_timestamp(row.get("timestamp"))
        if timestamp <= event_time:
            result.append(dict(row, timestamp=timestamp.isoformat()))
    return result


def within_window(timestamp, event_time, seconds: int, *, include_cutoff: bool = False) -> bool:
    """Check a past-facing event window while preserving its cutoff policy."""
    age = (normalize_timestamp(event_time) - normalize_timestamp(timestamp)).total_seconds()
    return 0 <= age and (age <= seconds if include_cutoff else age < seconds)
