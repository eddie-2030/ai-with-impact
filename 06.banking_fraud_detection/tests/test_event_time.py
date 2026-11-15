from datetime import datetime, timedelta, timezone

import pytest

from agents.investigation_agent import InvestigationAgent
from tools.pattern_matcher import PatternMatcherTool


EVENT = datetime(2020, 1, 15, 12, tzinfo=timezone.utc)


def transaction(**overrides):
    values = dict(transaction_id="current", user_id="account", amount=400,
                  timestamp=EVENT.isoformat(), location="Paris",
                  merchant_category="electronics", device_id="new")
    values.update(overrides)
    return values


def prior(transaction_id="prior", seconds=1, **overrides):
    values = dict(transaction_id=transaction_id, amount=100,
                  timestamp=(EVENT - timedelta(seconds=seconds)).isoformat(),
                  location="Detroit", merchant_category="groceries", device_id="known")
    values.update(overrides)
    return transaction(**values)


def test_replay_uses_event_time_and_equivalent_timezones():
    matcher = PatternMatcherTool()
    history = [prior(str(index), seconds=60 * (index + 1)) for index in range(6)]
    expected = matcher.execute(transaction(), history)
    assert "geographic_anomaly" in expected["patterns_detected"]
    assert "high_velocity" in expected["patterns_detected"]
    offset_history = [dict(t, timestamp=datetime.fromisoformat(t["timestamp"]).astimezone(
        timezone(timedelta(hours=9))).isoformat()) for t in history]
    assert matcher.execute(transaction(timestamp="2020-01-15T07:00:00-05:00"), offset_history) == expected
    shifted_history = [dict(t, timestamp=(datetime.fromisoformat(t["timestamp"]) + timedelta(days=1000)).isoformat()) for t in history]
    assert matcher.execute(transaction(timestamp=(EVENT + timedelta(days=1000)).isoformat()), shifted_history) == expected


def test_future_current_and_other_account_rows_cannot_influence_patterns():
    history = [prior(str(i), seconds=-1) for i in range(6)]
    history += [prior("current"), prior("other", user_id="other")]
    assert PatternMatcherTool().execute(transaction(), history)["patterns_detected"] == []


def test_history_window_boundaries_and_equal_time_peers():
    matcher = PatternMatcherTool()
    assert "geographic_anomaly" not in matcher.execute(transaction(), [prior(seconds=86400)])["patterns_detected"]
    assert "geographic_anomaly" in matcher.execute(transaction(), [prior(seconds=86399)])["patterns_detected"]
    assert "high_velocity" not in matcher.execute(transaction(), [prior(str(i), seconds=3600) for i in range(6)])["patterns_detected"]
    assert "high_velocity" in matcher.execute(transaction(), [prior(str(i), seconds=3599) for i in range(6)])["patterns_detected"]
    assert "high_velocity" in matcher.execute(transaction(), [prior(str(i), seconds=0) for i in range(6)])["patterns_detected"]


def test_investigation_uses_event_time_scoped_history():
    history = [prior("recent"), prior("boundary", seconds=86400), prior("old", seconds=86401),
               prior("future", seconds=-1), prior("current"), prior("other", user_id="other")]
    agent = InvestigationAgent()
    context = agent.execute({"transaction": transaction(), "user_history": history})["context"]
    assert context["transaction_count_24h"] == 2
    assert context["total_amount_24h"] == 200
    assert context["transaction_count_7d"] == 3
    assert context["unique_locations_7d"] == 1
    assert context["unique_devices_30d"] == 1


@pytest.mark.parametrize("bad_timestamp", ["invalid", "", 12345])
def test_malformed_timestamps_fail_consistently(bad_timestamp):
    for run in (
        lambda: PatternMatcherTool().execute(transaction(timestamp=bad_timestamp), []),
        lambda: PatternMatcherTool().execute(transaction(), [prior(timestamp=bad_timestamp)]),
        lambda: InvestigationAgent().execute({"transaction": transaction(timestamp=bad_timestamp)}),
        lambda: InvestigationAgent().execute({"transaction": transaction(), "user_history": [prior(timestamp=bad_timestamp)]}),
    ):
        with pytest.raises(ValueError, match="timestamp"):
            run()
