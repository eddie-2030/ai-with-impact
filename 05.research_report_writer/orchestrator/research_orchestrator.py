import uuid
from typing import Dict

from agents.analysis_agent import AnalysisAgent
from agents.fact_check_agent import FactCheckAgent
from agents.research_agent import ResearchAgent
from agents.synthesis_agent import SynthesisAgent, render_report


DEFAULT_MIN_CREDIBILITY = 0.5


class InsufficientEvidence(RuntimeError):
    code = "no_qualifying_sources"


class ResearchOrchestrator:
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.analysis_agent = AnalysisAgent()
        self.fact_check_agent = FactCheckAgent()
        self.synthesis_agent = SynthesisAgent()

    def execute_research(
        self, research_query: str, max_sources: int = 20,
        min_credibility_score: float = DEFAULT_MIN_CREDIBILITY,
    ) -> Dict:
        research = self.research_agent.execute({
            "query": research_query,
            "max_sources": max_sources,
        })
        mode = research["search_mode"]
        sources = research["sources"]
        findings = research["findings"]
        fixture = mode == "fixture"

        evidence_by_id = {
            finding["source_id"] for finding in findings if finding["content"].strip()
        }
        sources = [source for source in sources if source["source_id"] in evidence_by_id]
        if fixture:
            for source in sources:
                source["credibility_score"] = 0.0
                source["verification_status"] = "fixture"
        else:
            screened = self.fact_check_agent.execute({"sources": sources})["verifications"]
            scores = {record["source_id"]: record for record in screened}
            for source in sources:
                source.update(scores[source["source_id"]])
            sources = [
                source for source in sources
                if source["credibility_score"] >= min_credibility_score
            ]

        if not sources:
            raise InsufficientEvidence("No source excerpts met the report's evidence requirements.")

        source_by_id = {}
        for number, source in enumerate(sources, 1):
            source["reference_number"] = number
            source_by_id[source["source_id"]] = source

        findings = [
            finding for finding in findings
            if finding["source_id"] in source_by_id and finding["content"].strip()
        ]
        for finding in findings:
            finding["in_text_citation"] = f"[{source_by_id[finding['source_id']]['reference_number']}]"

        if fixture:
            sections = [
                (
                    source_by_id[finding["source_id"]]["title"],
                    finding["content"],
                    [source_by_id[finding["source_id"]]["reference_number"]],
                )
                for finding in findings
            ]
            report = render_report(sections, sources, self.synthesis_agent.citation_formatter, fixture=True)
        else:
            analysis = self.analysis_agent.execute({"query": research_query, "findings": findings})
            report = self.synthesis_agent.execute({
                "query": research_query,
                "findings": findings,
                "sources": sources,
                "analysis": analysis,
            })

        return {
            "request_id": str(uuid.uuid4()),
            "status": "completed",
            "research_query": research_query,
            "search_mode": mode,
            "report": report,
            "sources": sources,
            "findings": findings,
        }
