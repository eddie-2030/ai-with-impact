from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from db.db import init_db
from models.meeting_analyzer import AnalysisUnavailable, InvalidAnalysis
from services.meetings import MeetingConflict, MeetingInput, analyze_and_save, get_saved_meeting


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Meeting Notes Analyzer API", version="1.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    details = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
    return JSONResponse(status_code=422, content={"detail": details})


@app.post("/analyze")
def analyze(meeting: MeetingInput) -> dict:
    """Save an analysis or return the existing result for an identical input."""
    try:
        return analyze_and_save(meeting)
    except MeetingConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except AnalysisUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except InvalidAnalysis as error:
        raise HTTPException(status_code=502, detail=str(error)) from None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "meeting-analyzer"}


@app.get("/meetings/{meeting_id:path}")
def get_meeting(meeting_id: str) -> dict:
    meeting = get_saved_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


