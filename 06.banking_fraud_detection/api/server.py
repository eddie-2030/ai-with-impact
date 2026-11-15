from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, FiniteFloat
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from api.transaction_input import TransactionIn
from db.db import (
    Transaction, User, init_db, insert_fraud_alert, insert_risk_assessment,
    load_account_context, session_scope,
)
from orchestrator.fraud_orchestrator import FraudOrchestrator
from transaction_context import normalize_timestamp

logger = logging.getLogger(__name__)
orchestrator = FraudOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Banking Fraud Detection API", version="1.0", lifespan=lifespan)


class TransactionResponse(BaseModel):
    transaction_id: str
    status: str
    risk_score: FiniteFloat
    risk_level: str
    alert: dict[str, Any] | None
    patterns_detected: list[str]


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    details = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
    return JSONResponse(status_code=422, content={"detail": details})


def duplicate_transaction() -> HTTPException:
    return HTTPException(status_code=409, detail="Transaction ID already exists. Retrieve the original by ID.")


@app.post("/transactions", response_model=TransactionResponse)
def process_transaction(transaction: TransactionIn):
    """Assess and persist one new transaction."""
    transaction_id = transaction.transaction_id or str(uuid.uuid4())
    timestamp = transaction.timestamp or datetime.now(UTC).isoformat()
    data = transaction.model_dump()
    data.update(transaction_id=transaction_id, timestamp=timestamp)

    with session_scope() as session:
        existing = session.scalar(
            select(Transaction.id).where(Transaction.transaction_id == transaction_id)
        )
        if existing is not None:
            raise duplicate_transaction()
        user_history, user_profile = load_account_context(
            session, transaction.user_id, timestamp, transaction_id,
        )

    result = orchestrator.process_transaction(
        {**data, "amount": float(transaction.amount)},
        user_history=user_history,
        user_profile=user_profile,
        min_risk_score=70.0,
    )
    if result.get("status") == "error":
        logger.error("Transaction assessment failed")
        raise HTTPException(status_code=500, detail="Transaction assessment failed")

    response = TransactionResponse(
        transaction_id=transaction_id,
        status=result["status"],
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        alert=result.get("alert"),
        patterns_detected=result.get("patterns_detected", []),
    )

    with session_scope() as session:
        # Both unique IDs are arbitrated in PostgreSQL. A losing request rolls back
        # even a newly inserted user. Existing account attributes stay intact.
        session.execute(insert(User).values(user_id=transaction.user_id).on_conflict_do_nothing(
            index_elements=[User.user_id],
        ))
        saved_id = session.scalar(
            insert(Transaction)
            .values(**{**data, "timestamp": normalize_timestamp(timestamp).replace(tzinfo=None),
                       "status": response.status})
            .on_conflict_do_nothing(index_elements=[Transaction.transaction_id])
            .returning(Transaction.id)
        )
        if saved_id is None:
            raise duplicate_transaction()

        insert_risk_assessment(session, {
            "transaction_id": transaction_id,
            "risk_score": response.risk_score,
            "risk_level": response.risk_level,
            "risk_factors": result.get("risk_factors", {}),
            "agent_analysis": result.get("analysis", ""),
        })

        if response.alert:
            alert = response.alert
            insert_fraud_alert(session, {
                "alert_id": alert["alert_id"],
                "transaction_id": transaction_id,
                "user_id": transaction.user_id,
                "alert_type": alert["alert_type"],
                "severity": alert["severity"],
                "risk_score": alert["risk_score"],
                "description": alert["description"],
                "status": "open",
            })

    return response

@app.get("/transactions/{transaction_id:path}")
def get_transaction(transaction_id: str):
    """Get transaction details and fraud analysis"""
    from db.db import SessionLocal, Transaction, RiskAssessment, FraudAlert
    
    session = SessionLocal()
    try:
        db_transaction = session.query(Transaction).filter_by(transaction_id=transaction_id).first()
        if not db_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        risk_assessment = db_transaction.risk_assessment if db_transaction.risk_assessment else None
        alerts = db_transaction.alerts
        
        return {
            "transaction_id": db_transaction.transaction_id,
            "user_id": db_transaction.user_id,
            "amount": float(db_transaction.amount),
            "merchant": db_transaction.merchant,
            "location": db_transaction.location,
            "timestamp": normalize_timestamp(db_transaction.timestamp).isoformat(),
            "status": db_transaction.status,
            "risk_assessment": {
                "risk_score": risk_assessment.risk_score if risk_assessment else None,
                "risk_level": risk_assessment.risk_level if risk_assessment else None,
                "analysis": risk_assessment.agent_analysis if risk_assessment else None
            } if risk_assessment else None,
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "alert_type": alert.alert_type,
                    "status": alert.status
                }
                for alert in alerts
            ]
        }
    finally:
        session.close()

@app.get("/alerts")
def get_alerts(status: str | None = None, severity: str | None = None):
    """Get fraud alerts with optional filtering"""
    from db.db import SessionLocal, FraudAlert
    
    session = SessionLocal()
    try:
        query = session.query(FraudAlert)
        if status:
            query = query.filter_by(status=status)
        if severity:
            query = query.filter_by(severity=severity)
        
        alerts = query.order_by(FraudAlert.created_at.desc()).limit(100).all()
        
        return [
            {
                "alert_id": alert.alert_id,
                "transaction_id": alert.transaction_id,
                "user_id": alert.user_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "risk_score": alert.risk_score,
                "status": alert.status,
                "description": alert.description,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts
        ]
    finally:
        session.close()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fraud-detection"}

