from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from threading import Barrier
from unittest.mock import Mock

import pytest


def payload(**overrides):
    return {
        "transaction_id": "txn-safe",
        "user_id": "account",
        "amount": "12.34",
        "timestamp": "2026-11-15T14:00:00Z",
        **overrides,
    }


def stored_counts(db):
    with db.session_scope() as session:
        return [
            session.query(model).count()
            for model in (db.User, db.Transaction, db.RiskAssessment, db.FraudAlert)
        ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amount", "NaN"),
        ("amount", "Infinity"),
        ("amount", "0"),
        ("amount", "12.345"),
        ("amount", "0.001"),
        ("amount", "10000000000000.00"),
        ("latitude", 90.1),
        ("longitude", -180.1),
        ("latitude", "NaN"),
        ("longitude", "Infinity"),
        ("transaction_id", " "),
        ("user_id", "x" * 65),
        ("merchant", "Shop\0hidden"),
    ],
)
def test_invalid_inputs_do_not_score_or_write(client, database, monkeypatch, field, value):
    from api import server

    score = Mock(side_effect=AssertionError("Invalid inputs must not be scored"))
    monkeypatch.setattr(server.orchestrator, "process_transaction", score)

    response = client.post("/transactions", json=payload(**{field: value}))

    assert response.status_code == 422, response.text
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    score.assert_not_called()
    assert stored_counts(database) == [0, 0, 0, 0]


@pytest.mark.parametrize("amount", [float("nan"), float("inf")])
def test_nonstandard_json_numbers_return_redacted_validation_error(client, database, amount):
    response = client.post(
        "/transactions",
        content=json.dumps(payload(amount=amount, merchant="private-merchant.example")),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422, response.text
    assert "private-merchant.example" not in response.text
    assert response.json()["detail"][0]["loc"] == ["body", "amount"]
    assert stored_counts(database) == [0, 0, 0, 0]


def test_duplicate_id_is_rejected_before_scoring_and_keeps_original(client, database, monkeypatch):
    from api import server

    score = Mock(wraps=server.orchestrator.process_transaction)
    monkeypatch.setattr(server.orchestrator, "process_transaction", score)
    first = client.post("/transactions", json=payload())
    assert first.status_code == 200, first.text

    duplicate = client.post("/transactions", json=payload(user_id="other-account", amount="34.56"))

    assert duplicate.status_code == 409, duplicate.text
    assert score.call_count == 1
    assert stored_counts(database) == [1, 1, 1, 0]
    with database.session_scope() as session:
        transaction = session.query(database.Transaction).one()
        assert transaction.user_id == "account"
        assert transaction.amount == Decimal("12.34")
        assert transaction.risk_assessment.risk_score == first.json()["risk_score"]


def test_scoring_error_is_sanitized_and_leaves_no_records(client, database, monkeypatch):
    from api import server

    monkeypatch.setattr(
        server.orchestrator,
        "process_transaction",
        lambda *args, **kwargs: {
            "status": "error",
            "error": "internal-secret.example",
            "risk_score": 0,
            "risk_level": "unknown",
        },
    )

    response = client.post("/transactions", json=payload())

    assert response.status_code == 500, response.text
    assert "internal-secret.example" not in response.text
    assert stored_counts(database) == [0, 0, 0, 0]


@pytest.mark.parametrize("same_transaction_id", [True, False], ids=["duplicate-id", "new-shared-user"])
def test_concurrent_ingestion_persists_only_the_winning_rows(
    client, database, monkeypatch, same_transaction_id,
):
    from api import server

    at_scoring = Barrier(2, timeout=10)
    score = server.orchestrator.process_transaction

    def overlap(*args, **kwargs):
        at_scoring.wait()
        return score(*args, **kwargs)

    monkeypatch.setattr(server.orchestrator, "process_transaction", overlap)
    requests = [payload()]
    if same_transaction_id:
        requests.append(payload(user_id="other-account"))
    else:
        requests.append(payload(transaction_id="txn-distinct"))

    def submit(transaction):
        return client.post("/transactions", json=transaction)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(submit, requests))

    expected = [200, 409] if same_transaction_id else [200, 200]
    assert sorted(response.status_code for response in responses) == expected
    number_saved = expected.count(200)
    assert stored_counts(database) == [1, number_saved, number_saved, 0]
    saved_users = {
        transaction["user_id"]
        for transaction, response in zip(requests, responses)
        if response.status_code == 200
    }
    with database.session_scope() as session:
        assert {row.user_id for row in session.query(database.Transaction)} == saved_users
