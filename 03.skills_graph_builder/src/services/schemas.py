from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class PersonProfile(BaseModel):
    person_id: str
    name: Optional[str] = None
    org_unit: Optional[str] = None
    location: Optional[str] = None
    role_current: Optional[str] = None
    privacy_flags: Optional[Dict[str, bool]] = None

class ProjectEvidence(BaseModel):
    text: str
    source: str = "project_summary"
    timestamp: Optional[str] = None

class IngestProfileRequest(BaseModel):
    profile: PersonProfile
    evidence: List[ProjectEvidence] = Field(default_factory=list)

class RoleMatch(BaseModel):
    role_id: str
    title: str
    level: Optional[str] = None
    score: float

class HealthResponse(BaseModel):
    status: str = "ok"
