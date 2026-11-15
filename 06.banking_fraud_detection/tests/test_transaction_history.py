from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


EVENT = datetime(2020, 1, 15, 12, tzinfo=timezone.utc)


def seed_transaction(db, session, transaction_id, user_id, timestamp, **overrides):
    values = dict(
        transaction_id=transaction_id, user_id=user_id, amount=100,
        merchant_category="groceries", location="Detroit", device_id="known",
        timestamp=timestamp.replace(tzinfo=None), status="approved",
    )
    values.update(overrides)
    session.add(db.Transaction(**values))


def payload(transaction_id="current", user_id="account", **overrides):
    values = dict(
        transaction_id=transaction_id, user_id=user_id, amount=400,
        timestamp=EVENT.isoformat(), merchant_category="electronics",
        merchant="Shop", location="Paris", device_id="new",
    )
    values.update(overrides)
    return values


def test_post_loads_real_history_profile_and_preserves_account(client, database, monkeypatch):
    db = database
    with db.session_scope() as session:
        session.add(db.User(
            user_id="account", risk_profile="high", account_status="restricted",
            account_number="acct-1", email="owner@example.test", phone="555",
            registration_date=date(2019, 1, 1),
        ))
        session.add(db.User(user_id="other", risk_profile="low"))
        session.flush()
        session.add(db.UserProfile(
            user_id="account", avg_transaction_amount=Decimal("100.00"),
            typical_merchants=["groceries"], typical_locations=["Detroit"],
            device_fingerprints=["known"], spending_pattern={"weekly": 100},
        ))
        for index in range(6):
            seed_transaction(db, session, f"prior-{index}", "account", EVENT - timedelta(minutes=index + 1))
        seed_transaction(db, session, "future", "account", EVENT + timedelta(seconds=1),
                         amount=10000, merchant_category="electronics", location="Paris", device_id="new")
        seed_transaction(db, session, "other-account", "other", EVENT - timedelta(minutes=1),
                         amount=10000, merchant_category="electronics", location="Paris", device_id="new")

    from api import server
    observed = {}
    real_process = server.orchestrator.process_transaction

    def observe(transaction, **kwargs):
        observed.update(deepcopy(kwargs))
        observed["transaction"] = deepcopy(transaction)
        return real_process(transaction, **kwargs)

    monkeypatch.setattr(server.orchestrator, "process_transaction", observe)
    response = client.post("/transactions", json=payload())
    assert response.status_code == 200, response.text
    result = response.json()
    assert set(result["patterns_detected"]) == {
        "unusual_amount", "geographic_anomaly", "high_velocity", "unusual_merchant", "new_device"
    }
    assert result["risk_score"] == pytest.approx(48.9)
    assert result["alert"] is None  # Existing calibration/thresholds are deliberately unchanged.
    assert {t["transaction_id"] for t in observed["user_history"]} == {f"prior-{i}" for i in range(6)}
    assert observed["user_profile"]["risk_profile"] == "high"
    assert observed["user_profile"]["account_status"] == "restricted"
    assert observed["user_profile"]["typical_locations"] == ["Detroit"]
    assert observed["user_profile"]["device_fingerprints"] == ["known"]
    with db.session_scope() as session:
        user = session.query(db.User).filter_by(user_id="account").one()
        assert (user.risk_profile, user.account_status) == ("high", "restricted")
        assert (user.email, user.account_number, user.phone) == ("owner@example.test", "acct-1", "555")
        assert user.registration_date == date(2019, 1, 1)
        assert user.profile.spending_pattern == {"weekly": 100}
        assert user.profile.avg_transaction_amount == Decimal("100.00")
        assessment = session.query(db.RiskAssessment).filter_by(transaction_id="current").one()
        assert assessment.risk_factors["user_profile"]["score"] == 80
        assert assessment.risk_score == result["risk_score"]


def test_post_does_not_use_another_accounts_history(client, database):
    with database.session_scope() as session:
        session.add(database.User(user_id="account", risk_profile="high"))
        session.flush()
        for index in range(6):
            seed_transaction(database, session, f"other-{index}", "account", EVENT - timedelta(minutes=1))
    response = client.post("/transactions", json=payload(user_id="new-account"))
    assert response.status_code == 200
    assert response.json()["patterns_detected"] == []
    assert response.json()["risk_score"] == pytest.approx(3.8)
    with database.session_scope() as session:
        user = session.query(database.User).filter_by(user_id="new-account").one()
        assert (user.risk_profile, user.account_status) == ("low", "active")


def test_seeded_anomaly_persists_medium_alert_and_can_be_retrieved(client, database):
    """Exercise alert persistence under the unchanged score/threshold policy."""
    db = database
    event = EVENT.replace(hour=2)
    with db.session_scope() as session:
        session.add(db.User(user_id="account", risk_profile="high", account_status="active"))
        session.flush()
        for index in range(6):
            seed_transaction(db, session, f"prior-{index}", "account", event - timedelta(minutes=index + 1))

    response = client.post("/transactions", json=payload(amount=10000, timestamp=event.isoformat()))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "review"
    assert result["risk_score"] == pytest.approx(71.5)
    assert result["risk_level"] == "medium"
    assert set(result["patterns_detected"]) == {
        "unusual_amount", "geographic_anomaly", "high_velocity", "unusual_merchant", "new_device", "off_hours"
    }
    alert = result["alert"]
    assert alert is not None
    assert alert["alert_id"]
    assert (alert["transaction_id"], alert["user_id"]) == ("current", "account")
    assert (alert["severity"], alert["alert_type"]) == ("medium", "account_takeover")
    assert alert["risk_score"] == result["risk_score"]
    assert alert["investigation_recommendation"] == "STANDARD_REVIEW"

    with db.session_scope() as session:
        stored_transaction = session.query(db.Transaction).filter_by(transaction_id="current").one()
        assert (stored_transaction.user_id, stored_transaction.status) == ("account", "review")
        assert stored_transaction.timestamp == event.replace(tzinfo=None)
        assessment = session.query(db.RiskAssessment).filter_by(transaction_id="current").one()
        assert assessment.risk_score == result["risk_score"]
        assert assessment.risk_level == "medium"
        stored_alert = session.query(db.FraudAlert).filter_by(alert_id=alert["alert_id"]).one()
        assert (stored_alert.transaction_id, stored_alert.user_id) == ("current", "account")
        assert (stored_alert.severity, stored_alert.status) == ("medium", "open")
        assert stored_alert.risk_score == result["risk_score"]
        assert stored_alert.description == alert["description"]

    retrieved = client.get("/transactions/current")
    assert retrieved.status_code == 200, retrieved.text
    details = retrieved.json()
    assert details["status"] == "review"
    assert details["risk_assessment"]["risk_score"] == result["risk_score"]
    assert details["risk_assessment"]["risk_level"] == "medium"
    assert details["alerts"] == [{
        "alert_id": alert["alert_id"], "severity": "medium",
        "alert_type": "account_takeover", "status": "open",
    }]


@pytest.mark.parametrize(("amount", "score", "level", "status"), [
    ("8747.49", 69.99, "low", "approved"),
    ("8749.90", 70.0, "medium", "review"),
    ("10000.00", 72.5, "medium", "review"),
])
def test_scoring_label_and_alert_use_same_rounded_score(client, database, amount, score, level, status):
    event = EVENT.replace(hour=2)
    with database.session_scope() as session:
        session.add(database.User(user_id="account", risk_profile="high"))
        session.flush()
        seed_transaction(database, session, "prior", "account", event - timedelta(minutes=1))

    reply = client.post("/transactions", json=payload(
        amount=amount, timestamp=event.isoformat(), merchant_category="groceries",
    ))
    assert reply.status_code == 200, reply.text
    result = reply.json()
    assert result["risk_score"] == score
    assert result["risk_level"] == level
    assert result["status"] == status
    if status == "review":
        assert result["alert"]["severity"] == level
    else:
        assert result["alert"] is None


@pytest.mark.parametrize("content", ["bad\x00text", "\ud800"])
def test_unpersistable_optional_explanation_does_not_override_score(client, monkeypatch, content):
    from api import server

    provider = Mock()
    provider.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )
    monkeypatch.setattr(server.orchestrator.risk_agent, "client", provider)
    response = client.post("/transactions", json=payload())
    assert response.status_code == 200
    assert response.json()["risk_score"] == pytest.approx(3.8)
    saved = client.get("/transactions/current").json()
    assert saved["risk_assessment"]["analysis"].startswith("Risk analysis unavailable")
    provider.chat.completions.create.assert_called_once()


def test_post_normalizes_offset_and_naive_timestamps_to_utc(client, database):
    results = []
    for index, timestamp in enumerate(("2020-01-14T21:00:00-05:00", "2020-01-15T02:00:00Z", "2020-01-15T02:00:00")):
        response = client.post("/transactions", json=payload(
            transaction_id=f"tz-{index}", user_id=f"tz-account-{index}", timestamp=timestamp,
        ))
        assert response.status_code == 200
        results.append(response.json())
    assert all(r["patterns_detected"] == ["off_hours"] for r in results)
    assert all(r["risk_score"] == pytest.approx(24.8) for r in results)
    with database.session_scope() as session:
        assert {row.timestamp for row in session.query(database.Transaction).all()} == {datetime(2020, 1, 15, 2)}


def test_database_context_excludes_current_future_and_other_accounts(database):
    db = database
    with db.session_scope() as session:
        session.add_all([db.User(user_id="account"), db.User(user_id="other")])
        session.flush()
        seed_transaction(db, session, "current", "account", EVENT - timedelta(days=1))
        seed_transaction(db, session, "future", "account", EVENT + timedelta(microseconds=1))
        seed_transaction(db, session, "peer", "account", EVENT)
        seed_transaction(db, session, "past", "account", EVENT - timedelta(days=30))
        seed_transaction(db, session, "other", "other", EVENT)
    with db.session_scope() as session:
        history, profile = db.load_account_context(session, "account", "2020-01-15T07:00:00-05:00", "current")
        assert [t["transaction_id"] for t in history] == ["past", "peer"]
        assert all(datetime.fromisoformat(t["timestamp"]).utcoffset() == timedelta(0) for t in history)
        assert profile["risk_profile"] == "low"


@pytest.mark.parametrize("timestamp", ["garbage", "2020-99-99", "", "2020-01-15T25:00:00", 12345])
def test_invalid_timestamp_rejected_before_assessment_or_writes(client, database, monkeypatch, timestamp):
    from api import server

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid timestamps must be rejected before assessment")

    monkeypatch.setattr(server.orchestrator, "process_transaction", forbidden)
    response = client.post("/transactions", json=payload(timestamp=timestamp))
    assert response.status_code == 422
    with database.session_scope() as session:
        assert session.query(database.User).count() == 0
        assert session.query(database.Transaction).count() == 0
