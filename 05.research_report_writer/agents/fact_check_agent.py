from typing import Dict, Optional
from urllib.parse import urlsplit

from .base_agent import BaseAgent


class FactCheckAgent(BaseAgent):
    """Assign a heuristic source score for filtering."""

    def __init__(self):
        super().__init__(name="fact_check_agent", role="Source screening", allowed_tools=[])

    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        verifications = []
        for source in task["sources"]:
            host = urlsplit(source["url"]).hostname or ""
            institutional = host.rstrip(".").endswith((".gov", ".edu", ".ac.uk"))
            verifications.append({
                "source_id": source["source_id"],
                "credibility_score": 0.65 if institutional else 0.5,
                "verification_status": "heuristic",
            })
        return {"verifications": verifications, "status": "completed"}
