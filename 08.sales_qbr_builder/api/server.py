# api/server.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from db.db import (
    session_scope, init_db, upsert_qbr_request, create_qbr_pack,
    insert_insight, insert_data_source, insert_action_item, insert_approval, insert_metric
)
from models.qbr_analyzer import generate_qbr_insights, aggregate_qbr_data
from tools.mcp_clients import fetch_crm_data, fetch_analytics_data, fetch_support_data
import os
import uuid

app = FastAPI(title="Sales/CS QBR Pack Builder API", version="1.0")

class QBRRequestIn(BaseModel):
    account_id: str
    account_name: str
    quarter: Optional[str] = None
    period_start: date
    period_end: date
    goals: List[str] = Field(default_factory=list)

class QBRApprovalIn(BaseModel):
    action: str = Field(..., pattern="^(approve|request_changes|reject)$")
    approver_name: Optional[str] = None
    feedback: Optional[str] = None
    revision_notes: Optional[str] = None

class QBRRevisionIn(BaseModel):
    feedback: str
    clarifications: Optional[Dict[str, Any]] = None

class InsightOut(BaseModel):
    id: int
    insight_type: str
    title: str
    description: Optional[str]
    impact_score: Optional[float]
    confidence_score: Optional[float]
    category: Optional[str]

class QBRPackOut(BaseModel):
    pack_id: str
    executive_summary: Optional[str]
    account_health_score: Optional[float]
    status: str
    insights: List[InsightOut]
    action_items: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/qbr/generate")
async def generate_qbr(qbr_request: QBRRequestIn, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Generate a QBR pack for an account"""
    
    request_id = f"qbr-{uuid.uuid4().hex[:8]}"
    pack_id = f"pack-{uuid.uuid4().hex[:8]}"
    
    # Create QBR request
    with session_scope() as s:
        db_request = upsert_qbr_request(s, {
            "request_id": request_id,
            "account_id": qbr_request.account_id,
            "account_name": qbr_request.account_name,
            "quarter": qbr_request.quarter,
            "period_start": qbr_request.period_start,
            "period_end": qbr_request.period_end,
            "goals": qbr_request.goals,
            "status": "processing"
        })
        
        # Create QBR pack
        db_pack = create_qbr_pack(s, {
            "qbr_request_id": db_request.id,
            "pack_id": pack_id,
            "status": "draft"
        })
    
    # Process QBR in background
    background_tasks.add_task(
        process_qbr_generation,
        request_id=request_id,
        pack_id=pack_id,
        account_id=qbr_request.account_id,
        account_name=qbr_request.account_name,
        period_start=qbr_request.period_start,
        period_end=qbr_request.period_end,
        goals=qbr_request.goals
    )
    
    return {
        "request_id": request_id,
        "pack_id": pack_id,
        "status": "processing",
        "message": "QBR generation started. Use GET /qbr/{pack_id} to check status."
    }

async def process_qbr_generation(
    request_id: str,
    pack_id: str,
    account_id: str,
    account_name: str,
    period_start: date,
    period_end: date,
    goals: List[str]
):
    """Background task to process QBR generation"""
    try:
        # Fetch data from MCP servers (parallel)
        crm_data = fetch_crm_data(account_id, period_start, period_end)
        analytics_data = fetch_analytics_data(account_id, period_start, period_end)
        support_data = fetch_support_data(account_id, period_start, period_end)
        
        # Aggregate and validate data
        aggregated_data = aggregate_qbr_data(crm_data, analytics_data, support_data)
        
        # Generate insights using LLM
        insights_result = generate_qbr_insights(
            account_name=account_name,
            aggregated_data=aggregated_data,
            goals=goals,
            period_start=period_start,
            period_end=period_end
        )
        
        # Store results in database
        with session_scope() as s:
            from db.db import QBRPack, QBRRequest
            
            # Update pack
            pack = s.query(QBRPack).filter_by(pack_id=pack_id).first()
            if pack:
                pack.executive_summary = insights_result.get("executive_summary")
                pack.account_health_score = insights_result.get("account_health_score")
                pack.status = "pending_approval"
            
            # Store insights
            for insight in insights_result.get("insights", []):
                insert_insight(s, {
                    "qbr_pack_id": pack.id,
                    "insight_type": insight.get("type"),
                    "title": insight.get("title"),
                    "description": insight.get("description"),
                    "impact_score": insight.get("impact_score"),
                    "confidence_score": insight.get("confidence_score"),
                    "category": insight.get("category")
                })
            
            # Store data sources
            insert_data_source(s, {
                "qbr_pack_id": pack.id,
                "source_type": "crm",
                "source_name": "CRM",
                "data_json": crm_data,
                "data_quality_score": 0.95
            })
            insert_data_source(s, {
                "qbr_pack_id": pack.id,
                "source_type": "analytics",
                "source_name": "Analytics",
                "data_json": analytics_data,
                "data_quality_score": 0.90
            })
            insert_data_source(s, {
                "qbr_pack_id": pack.id,
                "source_type": "support",
                "source_name": "Support",
                "data_json": support_data,
                "data_quality_score": 0.85
            })
            
            # Store action items
            for action in insights_result.get("action_items", []):
                insert_action_item(s, {
                    "qbr_pack_id": pack.id,
                    "description": action.get("description"),
                    "assignee": action.get("assignee"),
                    "due_date": datetime.fromisoformat(action["due_date"]).date() if action.get("due_date") else None,
                    "priority": action.get("priority", "medium"),
                    "status": "open"
                })
            
            # Store metrics
            for metric in insights_result.get("metrics", []):
                insert_metric(s, {
                    "qbr_pack_id": pack.id,
                    "metric_name": metric.get("name"),
                    "metric_value": metric.get("value"),
                    "metric_unit": metric.get("unit"),
                    "period_start": period_start,
                    "period_end": period_end,
                    "comparison_value": metric.get("comparison_value"),
                    "change_percent": metric.get("change_percent"),
                    "trend": metric.get("trend")
                })
            
            # Update request status
            request = s.query(QBRRequest).filter_by(request_id=request_id).first()
            if request:
                request.status = "completed"
    
    except Exception as e:
        # Update status to failed
        with session_scope() as s:
            from db.db import QBRRequest, QBRPack
            request = s.query(QBRRequest).filter_by(request_id=request_id).first()
            if request:
                request.status = "failed"
            pack = s.query(QBRPack).filter_by(pack_id=pack_id).first()
            if pack:
                pack.status = "failed"

@app.get("/qbr/{pack_id}")
async def get_qbr(pack_id: str) -> Dict[str, Any]:
    """Get QBR pack by pack_id"""
    from db.db import SessionLocal, QBRPack, Insight, ActionItem, Metric
    
    session = SessionLocal()
    try:
        pack = session.query(QBRPack).filter_by(pack_id=pack_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="QBR pack not found")
        
        insights = session.query(Insight).filter_by(qbr_pack_id=pack.id).all()
        action_items = session.query(ActionItem).filter_by(qbr_pack_id=pack.id).all()
        metrics = session.query(Metric).filter_by(qbr_pack_id=pack.id).all()
        
        return {
            "pack_id": pack.pack_id,
            "executive_summary": pack.executive_summary,
            "account_health_score": pack.account_health_score,
            "status": pack.status,
            "version": pack.version,
            "insights": [
                {
                    "id": i.id,
                    "type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "impact_score": i.impact_score,
                    "confidence_score": i.confidence_score,
                    "category": i.category
                }
                for i in insights
            ],
            "action_items": [
                {
                    "id": ai.id,
                    "description": ai.description,
                    "assignee": ai.assignee,
                    "due_date": ai.due_date.isoformat() if ai.due_date else None,
                    "priority": ai.priority,
                    "status": ai.status
                }
                for ai in action_items
            ],
            "metrics": [
                {
                    "id": m.id,
                    "name": m.metric_name,
                    "value": m.metric_value,
                    "unit": m.metric_unit,
                    "change_percent": m.change_percent,
                    "trend": m.trend
                }
                for m in metrics
            ],
            "created_at": pack.created_at.isoformat(),
            "updated_at": pack.updated_at.isoformat()
        }
    finally:
        session.close()

@app.post("/qbr/{pack_id}/approve")
async def approve_qbr(pack_id: str, approval: QBRApprovalIn) -> Dict[str, Any]:
    """Approve, request changes, or reject a QBR pack"""
    from db.db import SessionLocal, QBRPack
    
    session = SessionLocal()
    try:
        pack = session.query(QBRPack).filter_by(pack_id=pack_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="QBR pack not found")
        
        # Record approval
        insert_approval(session, {
            "qbr_pack_id": pack.id,
            "approver_name": approval.approver_name,
            "action": approval.action,
            "feedback": approval.feedback,
            "revision_notes": approval.revision_notes
        })
        
        # Update pack status
        if approval.action == "approve":
            pack.status = "approved"
            pack.approved_at = datetime.utcnow()
        elif approval.action == "request_changes":
            pack.status = "draft"
            pack.version += 1
        elif approval.action == "reject":
            pack.status = "rejected"
        
        session.commit()
        
        return {
            "pack_id": pack_id,
            "status": pack.status,
            "action": approval.action,
            "message": f"QBR pack {approval.action}d successfully"
        }
    finally:
        session.close()

@app.post("/qbr/{pack_id}/revise")
async def revise_qbr(pack_id: str, revision: QBRRevisionIn) -> Dict[str, Any]:
    """Request revisions to a QBR pack"""
    from db.db import SessionLocal, QBRPack
    
    session = SessionLocal()
    try:
        pack = session.query(QBRPack).filter_by(pack_id=pack_id).first()
        if not pack:
            raise HTTPException(status_code=404, detail="QBR pack not found")
        
        pack.status = "draft"
        pack.version += 1
        session.commit()
        
        return {
            "pack_id": pack_id,
            "status": "draft",
            "message": "QBR pack marked for revision. Use POST /qbr/generate to regenerate."
        }
    finally:
        session.close()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "qbr-builder"}
