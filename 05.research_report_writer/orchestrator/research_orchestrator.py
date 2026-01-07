# orchestrator/research_orchestrator.py
import uuid
from typing import Dict, Optional
from datetime import datetime
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.fact_check_agent import FactCheckAgent
from agents.synthesis_agent import SynthesisAgent

class ResearchOrchestrator:
    """Orchestrates the multi-agent research workflow"""
    
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.analysis_agent = AnalysisAgent()
        self.fact_check_agent = FactCheckAgent()
        self.synthesis_agent = SynthesisAgent()
    
    def execute_research(self, research_query: str, max_sources: int = 20, 
                        min_credibility_score: float = 0.6) -> Dict:
        """Execute complete research workflow"""
        
        request_id = str(uuid.uuid4())
        
        try:
            # Step 1: Research Agent - Gather Information
            research_task = {
                "query": research_query,
                "max_sources": max_sources
            }
            research_result = self.research_agent.execute(research_task)
            findings = research_result.get("findings", [])
            sources = research_result.get("sources", [])
            
            if not findings:
                return {
                    "request_id": request_id,
                    "status": "failed",
                    "error": "No findings gathered",
                    "report": None
                }
            
            # Step 2: Fact-Check Agent - Verify Sources (can run in parallel with analysis)
            fact_check_task = {
                "sources": sources,
                "findings": findings
            }
            verification_result = self.fact_check_agent.execute(fact_check_task)
            verifications = verification_result.get("verifications", [])
            
            # Update sources with verification results
            verification_map = {v["source_id"]: v for v in verifications}
            for source in sources:
                verification = verification_map.get(source.get("source_id"), {})
                source["credibility_score"] = verification.get("credibility_score", 0.5)
                source["verification_status"] = verification.get("verification_status", "pending")
            
            # Step 3: Analysis Agent - Analyze Findings
            analysis_task = {
                "query": research_query,
                "findings": findings
            }
            analysis_result = self.analysis_agent.execute(analysis_task)
            
            # Step 4: Synthesis Agent - Generate Report
            synthesis_task = {
                "query": research_query,
                "findings": findings,
                "sources": sources,
                "analysis": analysis_result
            }
            synthesis_context = {
                "min_credibility_score": min_credibility_score
            }
            synthesis_result = self.synthesis_agent.execute(synthesis_task, synthesis_context)
            
            return {
                "request_id": request_id,
                "status": "completed",
                "research_query": research_query,
                "report": {
                    "content": synthesis_result.get("report_content", ""),
                    "executive_summary": synthesis_result.get("executive_summary", ""),
                    "references": synthesis_result.get("references", ""),
                    "word_count": synthesis_result.get("word_count", 0),
                    "source_count": synthesis_result.get("source_count", 0)
                },
                "sources": sources,
                "findings": findings,
                "analysis": analysis_result,
                "verifications": verifications
            }
        
        except Exception as e:
            return {
                "request_id": request_id,
                "status": "failed",
                "error": str(e),
                "report": None
            }


