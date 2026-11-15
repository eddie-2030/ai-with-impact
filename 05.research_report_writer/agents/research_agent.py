"""Turn provider excerpts into findings linked to their source records."""

import uuid
from datetime import UTC, datetime
from typing import Dict, Optional

from tools.web_search import SearchUnavailable

from .base_agent import BaseAgent


class ResearchAgent(BaseAgent):
    """Collect source metadata and evidence without visiting result URLs."""

    def __init__(self):
        super().__init__(
            name="research_agent",
            role="Information Gathering",
            allowed_tools=["web_search"],
        )

    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        search_results = self.use_tool(
            "web_search", query=task.get("query", ""), num_results=task.get("max_sources", 10)
        )
        if not search_results:
            raise SearchUnavailable("search_no_results", "Search returned no usable sources.")

        access_date = datetime.now(UTC).date().isoformat()
        sources = []
        findings = []
        for result in search_results:
            source_id = str(uuid.uuid4())
            provider = result["provider"]
            source = {
                "source_id": source_id,
                "title": result["title"],
                "authors": [],
                "publication_date": result["publication_date"],
                "url": result["url"],
                "source_type": "fixture" if provider == "fixture" else "website",
                "publisher": "",
                "access_date": access_date,
                "provider": provider,
                "rank": result["rank"],
            }
            if "score" in result:
                source["search_score"] = result["score"]
            sources.append(source)
            findings.append({"content": result["snippet"], "source_id": source_id})

        return {
            "findings": findings,
            "sources": sources,
            "search_mode": search_results[0]["provider"],
            "status": "completed",
        }
