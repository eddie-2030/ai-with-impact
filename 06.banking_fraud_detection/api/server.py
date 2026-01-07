# api/server.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from db.db import session_scope, init_db, upsert_user, insert_transaction, insert_risk_assessment, insert_fraud_alert
from orchestrator.fraud_orchestrator import FraudOrchestrator
import uuid

app = FastAPI(title="Banking Fraud Detection API", version="1.0")

orchestrator = FraudOrchestrator()

class TransactionIn(BaseModel):
    transaction_id: Optional[str] = None
    user_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD")
    merchant: Optional[str] = None
    merchant_category: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    transaction_type: str = Field(default="purchase")
    payment_method: str = Field(default="card")
    timestamp: Optional[str] = None

class TransactionResponse(BaseModel):
    transaction_id: str
    status: str
    risk_score: float
    risk_level: str
    alert: Optional[Dict[str, Any]]
    patterns_detected: List[str]

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/transactions", response_model=TransactionResponse)
async def process_transaction(transaction: TransactionIn):
    """Process a transaction for fraud detection"""
    
    transaction_id = transaction.transaction_id or str(uuid.uuid4())
    timestamp = transaction.timestamp or datetime.utcnow().isoformat()
    
    transaction_dict = {
        "transaction_id": transaction_id,
        "user_id": transaction.user_id,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "merchant": transaction.merchant,
        "merchant_category": transaction.merchant_category,
        "location": transaction.location,
        "latitude": transaction.latitude,
        "longitude": transaction.longitude,
        "device_id": transaction.device_id,
        "ip_address": transaction.ip_address,
        "transaction_type": transaction.transaction_type,
        "payment_method": transaction.payment_method,
        "timestamp": timestamp
    }
    
    # Get user history (simplified - in production, query database)
    user_history = []  # Would query from database
    
    # Get user profile (simplified - in production, query database)
    user_profile = {"risk_profile": "low"}  # Would query from database
    
    # Process transaction through orchestrator
    result = orchestrator.process_transaction(
        transaction_dict,
        user_history=user_history,
        user_profile=user_profile,
        min_risk_score=70.0
    )
    
    # Store in database
    with session_scope() as s:
        # Upsert user
        user = upsert_user(s, {
            "user_id": transaction.user_id,
            "account_status": "active",
            "risk_profile": "low"
        })
        s.flush()
        
        # Insert transaction
        db_transaction = insert_transaction(s, {
            "transaction_id": transaction_id,
            "user_id": transaction.user_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "merchant": transaction.merchant,
            "merchant_category": transaction.merchant_category,
            "location": transaction.location,
            "latitude": transaction.latitude,
            "longitude": transaction.longitude,
            "device_id": transaction.device_id,
            "ip_address": transaction.ip_address,
            "transaction_type": transaction.transaction_type,
            "payment_method": transaction.payment_method,
            "timestamp": datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
            "status": result.get("status", "pending")
        })
        s.flush()
        
        # Insert risk assessment
        insert_risk_assessment(s, {
            "transaction_id": transaction_id,
            "risk_score": result.get("risk_score", 0.0),
            "risk_level": result.get("risk_level", "low"),
            "risk_factors": result.get("risk_factors", {}),
            "agent_analysis": result.get("analysis", "")
        })
        
        # Insert alert if generated
        if result.get("alert"):
            alert_data = result["alert"]
            insert_fraud_alert(s, {
                "alert_id": alert_data.get("alert_id"),
                "transaction_id": transaction_id,
                "user_id": transaction.user_id,
                "alert_type": alert_data.get("alert_type"),
                "severity": alert_data.get("severity"),
                "risk_score": alert_data.get("risk_score", 0.0),
                "description": alert_data.get("description"),
                "status": "open"
            })
    
    return TransactionResponse(
        transaction_id=transaction_id,
        status=result.get("status", "approved"),
        risk_score=result.get("risk_score", 0.0),
        risk_level=result.get("risk_level", "low"),
        alert=result.get("alert"),
        patterns_detected=result.get("patterns_detected", [])
    )

@app.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
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
            "timestamp": db_transaction.timestamp.isoformat(),
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
async def get_alerts(status: Optional[str] = None, severity: Optional[str] = None):
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

