# api/server.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from db.db import session_scope, init_db, ResearchRequest, Source, ResearchFinding, ResearchReport, SourceVerification
from orchestrator.research_orchestrator import ResearchOrchestrator
import uuid

app = FastAPI(title="Research Report Writer API", version="1.0")

orchestrator = ResearchOrchestrator()

class ResearchRequestIn(BaseModel):
    research_query: str = Field(..., min_length=10)
    research_type: str = Field(default="comprehensive")
    max_sources: int = Field(default=20, ge=1, le=50)
    min_credibility_score: float = Field(default=0.6, ge=0.0, le=1.0)

class ResearchResponse(BaseModel):
    request_id: str
    status: str
    research_query: str
    report: Optional[Dict[str, Any]]
    source_count: Optional[int]
    created_at: str

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/research", response_model=ResearchResponse)
async def create_research(request: ResearchRequestIn):
    """Create a research report"""
    
    request_id = str(uuid.uuid4())
    
    try:
        # Execute research workflow
        result = orchestrator.execute_research(
            research_query=request.research_query,
            max_sources=request.max_sources,
            min_credibility_score=request.min_credibility_score
        )
        
        # Store in database
        with session_scope() as s:
            db_request = ResearchRequest(
                request_id=request_id,
                research_query=request.research_query,
                research_type=request.research_type,
                status=result.get("status", "completed"),
                max_sources=request.max_sources,
                completed_at=datetime.utcnow() if result.get("status") == "completed" else None
            )
            s.add(db_request)
            s.flush()
            
            # Store sources
            sources_map = {}
            for source_data in result.get("sources", []):
                db_source = Source(
                    source_id=source_data.get("source_id"),
                    research_request_id=db_request.id,
                    title=source_data.get("title", ""),
                    authors=source_data.get("authors", []),
                    publication_date=datetime.fromisoformat(source_data["publication_date"]).date() 
                        if source_data.get("publication_date") else None,
                    url=source_data.get("url"),
                    doi=source_data.get("doi"),
                    source_type=source_data.get("source_type"),
                    publisher=source_data.get("publisher"),
                    access_date=datetime.fromisoformat(source_data["access_date"]).date()
                        if source_data.get("access_date") else datetime.now().date(),
                    credibility_score=source_data.get("credibility_score", 0.0),
                    verification_status=source_data.get("verification_status", "pending")
                )
                s.add(db_source)
                sources_map[source_data.get("source_id")] = db_source
            
            s.flush()
            
            # Store findings
            for finding_data in result.get("findings", []):
                source_id = finding_data.get("source_id")
                db_source = sources_map.get(source_id)
                if db_source:
                    db_finding = ResearchFinding(
                        research_request_id=db_request.id,
                        source_id=db_source.id,
                        content=finding_data.get("content", ""),
                        quote=finding_data.get("quote"),
                        page_number=finding_data.get("page_number"),
                        in_text_citation=finding_data.get("in_text_citation"),
                        confidence_score=finding_data.get("confidence_score", 0.5),
                        agent_type="research"
                    )
                    s.add(db_finding)
            
            # Store report
            if result.get("report"):
                report_data = result["report"]
                db_report = ResearchReport(
                    research_request_id=db_request.id,
                    report_content=report_data.get("content", ""),
                    executive_summary=report_data.get("executive_summary", ""),
                    references_section=report_data.get("references", ""),
                    word_count=report_data.get("word_count", 0),
                    source_count=report_data.get("source_count", 0)
                )
                s.add(db_report)
        
        return ResearchResponse(
            request_id=request_id,
            status=result.get("status", "completed"),
            research_query=request.research_query,
            report=result.get("report"),
            source_count=result.get("report", {}).get("source_count", 0) if result.get("report") else 0,
            created_at=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")

@app.get("/research/{request_id}")
async def get_research(request_id: str):
    """Get research report by request_id"""
    from db.db import SessionLocal
    
    session = SessionLocal()
    try:
        db_request = session.query(ResearchRequest).filter_by(request_id=request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Research request not found")
        
        report = db_request.report if db_request.report else None
        
        return {
            "request_id": db_request.request_id,
            "research_query": db_request.research_query,
            "status": db_request.status,
            "report": {
                "content": report.report_content if report else None,
                "executive_summary": report.executive_summary if report else None,
                "references": report.references_section if report else None,
                "word_count": report.word_count if report else None,
                "source_count": report.source_count if report else None
            } if report else None,
            "created_at": db_request.created_at.isoformat(),
            "completed_at": db_request.completed_at.isoformat() if db_request.completed_at else None
        }
    finally:
        session.close()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "research-report-writer"}

