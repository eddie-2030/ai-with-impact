from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ClauseComparison(BaseModel):
    clause_id: str
    title: str
    template_text: str
    matched_text: Optional[str] = None
    similarity: float = 0.0
    risk_flags: List[str] = []

class AnalysisRequest(BaseModel):
    template_name: str = Field(default="master_service_agreement")

class AnalysisResult(BaseModel):
    template_name: str
    overall_risk: float
    risk_band: str
    missing_clauses: List[str]
    clause_results: List[ClauseComparison]
    global_flags: List[str] = []
