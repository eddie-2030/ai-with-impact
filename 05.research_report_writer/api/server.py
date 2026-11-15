from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from agents.base_agent import ModelUnavailable
from db.db import (
    ResearchFinding, ResearchReport, ResearchRequest, Source, SourceVerification,
    init_db, session_scope,
)
from orchestrator.research_orchestrator import (
    DEFAULT_MIN_CREDIBILITY, InsufficientEvidence, ResearchOrchestrator,
)
from tools.web_search import SearchUnavailable

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Research Report Writer API", version="1.0", lifespan=lifespan)
orchestrator = ResearchOrchestrator()


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, exc: RequestValidationError):
    # The submitted input can contain a lone surrogate that JSONResponse cannot encode.
    errors = [
        {key: error[key] for key in ("loc", "msg", "type")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


class ResearchRequestIn(BaseModel):
    research_query: str = Field(..., min_length=10, max_length=4000)
    research_type: str = Field(default="comprehensive", max_length=50)
    max_sources: int = Field(default=20, ge=1, le=50)
    min_credibility_score: float = Field(default=DEFAULT_MIN_CREDIBILITY, ge=0.0, le=1.0)

    @field_validator("research_query", "research_type")
    @classmethod
    def database_text(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Text cannot contain NUL characters.")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("Text must be valid UTF-8.") from exc
        return value


class ResearchResponse(BaseModel):
    request_id: str
    status: str
    research_query: str
    report: dict[str, Any]
    source_count: int
    created_at: str
    search_mode: str
    sources: list[dict[str, Any]]


def _source_view(source: Source) -> dict:
    details = source.verification.verification_details if source.verification else None
    if not isinstance(details, dict):
        details = {}
    return {
        "source_id": source.source_id,
        "title": source.title,
        "url": source.url,
        "source_type": source.source_type,
        "publication_date": source.publication_date.isoformat() if source.publication_date else None,
        "credibility_score": source.credibility_score,
        "verification_status": source.verification_status,
        "search_mode": details.get("search_mode"),
        "rank": details.get("rank"),
        "search_score": details.get("search_score"),
        "reference_number": details.get("reference_number"),
    }


def _failure(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


@app.post("/research", response_model=ResearchResponse)
def create_research(request: ResearchRequestIn):
    try:
        result = orchestrator.execute_research(
            research_query=request.research_query,
            max_sources=request.max_sources,
            min_credibility_score=request.min_credibility_score,
        )
    except SearchUnavailable as exc:
        invalid_input = exc.code in {"search_invalid_input", "search_no_results"}
        raise _failure(422 if invalid_input else 503, exc.code, str(exc)) from exc
    except InsufficientEvidence as exc:
        raise _failure(422, exc.code, str(exc)) from exc
    except ModelUnavailable as exc:
        raise _failure(503, exc.code, str(exc)) from exc

    report = result["report"]
    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        with session_scope() as session:
            db_request = ResearchRequest(
                request_id=result["request_id"],
                research_query=request.research_query,
                research_type=request.research_type,
                status="completed",
                max_sources=request.max_sources,
                created_at=created_at,
                completed_at=created_at,
            )
            session.add(db_request)
            sources_by_id = {}
            for data in result["sources"]:
                publication_date = data.get("publication_date")
                access_date = data.get("access_date")
                source = Source(
                    source_id=data["source_id"],
                    research_request=db_request,
                    title=data["title"],
                    authors=data.get("authors", []),
                    publication_date=date.fromisoformat(publication_date) if publication_date else None,
                    url=data["url"],
                    doi=data.get("doi"),
                    source_type=data.get("source_type", "website"),
                    publisher=data.get("publisher"),
                    access_date=date.fromisoformat(access_date) if access_date else created_at.date(),
                    credibility_score=data["credibility_score"],
                    verification_status=data["verification_status"],
                )
                source.verification = SourceVerification(verification_details={
                    "search_mode": result["search_mode"],
                    "rank": data.get("rank"),
                    "search_score": data.get("search_score"),
                    "reference_number": data["reference_number"],
                })
                session.add(source)
                sources_by_id[data["source_id"]] = source

            for finding in result["findings"]:
                session.add(ResearchFinding(
                    research_request=db_request,
                    source=sources_by_id[finding["source_id"]],
                    content=finding["content"],
                    in_text_citation=finding["in_text_citation"],
                    agent_type="research",
                ))

            session.add(ResearchReport(
                research_request=db_request,
                report_content=report["content"],
                executive_summary=report["executive_summary"],
                references_section=report["references"],
                word_count=report["word_count"],
                source_count=report["source_count"],
            ))
            sources = [_source_view(source) for source in sources_by_id.values()]
    except SQLAlchemyError as exc:
        logger.error("Research report could not be saved.")
        raise _failure(500, "report_storage_error", "The report could not be saved.") from exc

    return ResearchResponse(
        request_id=result["request_id"],
        status="completed",
        research_query=request.research_query,
        report=report,
        source_count=report["source_count"],
        created_at=created_at.isoformat(),
        search_mode=result["search_mode"],
        sources=sources,
    )


@app.get("/research/{request_id}")
def get_research(request_id: str):
    from db.db import SessionLocal

    with SessionLocal() as session:
        db_request = session.query(ResearchRequest).filter_by(request_id=request_id).first()
        if db_request is None:
            raise HTTPException(status_code=404, detail="Research request not found")

        report = db_request.report
        sources = sorted(
            (_source_view(source) for source in db_request.sources),
            key=lambda source: source.get("reference_number") or 0,
        )
        return {
            "request_id": db_request.request_id,
            "research_query": db_request.research_query,
            "status": db_request.status,
            "report": {
                "content": report.report_content,
                "executive_summary": report.executive_summary,
                "references": report.references_section,
                "word_count": report.word_count,
                "source_count": report.source_count,
            } if report else None,
            "source_count": report.source_count if report else 0,
            "sources": sources,
            "search_mode": sources[0].get("search_mode") if sources else None,
            "created_at": db_request.created_at.isoformat(),
            "completed_at": db_request.completed_at.isoformat() if db_request.completed_at else None,
        }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "research-report-writer"}
