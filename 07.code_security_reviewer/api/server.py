# api/server.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from db.db import session_scope, init_db
from orchestrator.code_review_orchestrator import CodeReviewOrchestrator
import uuid

app = FastAPI(title="Code Security Reviewer API", version="1.0")

orchestrator = CodeReviewOrchestrator()

class CodeReviewRequest(BaseModel):
    code: str = Field(..., description="Code to review")
    language: str = Field(default="python", description="Programming language")
    file_path: Optional[str] = None

class CodeReviewResponse(BaseModel):
    review_id: str
    status: str
    security: Dict[str, Any]
    performance: Dict[str, Any]
    quality: Dict[str, Any]
    rewrites: List[Dict[str, Any]]
    summary: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/review", response_model=CodeReviewResponse)
async def review_code(request: CodeReviewRequest):
    """Review code for security, performance, and quality issues"""
    
    result = orchestrator.review_code(
        code=request.code,
        language=request.language,
        file_path=request.file_path
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Review failed"))
    
    # Store in database (simplified - would store all findings)
    with session_scope() as s:
        from db.db import CodeReview, ReviewSummary
        
        review = CodeReview(
            review_id=result["review_id"],
            code_content=request.code,
            language=request.language,
            file_path=request.file_path,
            status="completed",
            completed_at=datetime.utcnow()
        )
        s.add(review)
        s.flush()
        
        summary_data = result.get("summary", {})
        summary = ReviewSummary(
            review_id=review.id,
            security_score=summary_data.get("security_score"),
            performance_score=summary_data.get("performance_score"),
            quality_score=summary_data.get("quality_score"),
            overall_score=summary_data.get("overall_score"),
            total_findings=summary_data.get("total_findings", 0),
            critical_findings=summary_data.get("critical_findings", 0),
            high_findings=summary_data.get("high_findings", 0),
            medium_findings=summary_data.get("medium_findings", 0),
            low_findings=summary_data.get("low_findings", 0),
            summary_text=summary_data.get("summary", ""),
            recommendations=summary_data.get("recommendations", "")
        )
        s.add(summary)
    
    return CodeReviewResponse(
        review_id=result["review_id"],
        status=result["status"],
        security=result.get("security", {}),
        performance=result.get("performance", {}),
        quality=result.get("quality", {}),
        rewrites=result.get("rewrites", []),
        summary=result.get("summary", {})
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "code-security-reviewer"}

