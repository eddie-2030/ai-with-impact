# orchestrator/code_review_orchestrator.py
import uuid
from typing import Dict, Optional
from datetime import datetime
from agents.code_analyzer_agent import CodeAnalyzerAgent
from agents.security_agent import SecurityAgent
from agents.performance_agent import PerformanceAgent
from agents.quality_agent import QualityAgent
from agents.code_rewriter_agent import CodeRewriterAgent
from agents.review_coordinator import ReviewCoordinator

class CodeReviewOrchestrator:
    """Orchestrates the multi-agent code review workflow"""
    
    def __init__(self):
        self.analyzer_agent = CodeAnalyzerAgent()
        self.security_agent = SecurityAgent()
        self.performance_agent = PerformanceAgent()
        self.quality_agent = QualityAgent()
        self.rewriter_agent = CodeRewriterAgent()
        self.coordinator = ReviewCoordinator()
    
    def review_code(self, code: str, language: str = "python",
                   file_path: Optional[str] = None) -> Dict:
        """Review code through multi-agent workflow"""
        
        review_id = str(uuid.uuid4())
        
        try:
            # Step 1: Code Analyzer Agent
            analyzer_task = {"code": code, "language": language}
            code_analysis = self.analyzer_agent.execute(analyzer_task)
            
            # Step 2: Security Agent
            security_task = {"code": code, "language": language}
            security_results = self.security_agent.execute(security_task)
            
            # Step 3: Performance Agent
            performance_task = {"code": code, "language": language}
            performance_results = self.performance_agent.execute(performance_task)
            
            # Step 4: Quality Agent
            quality_task = {"code": code, "language": language}
            quality_results = self.quality_agent.execute(quality_task)
            
            # Step 5: Code Rewriter Agent
            rewriter_task = {
                "code": code,
                "language": language,
                "security_findings": security_results.get("findings", []),
                "performance_findings": performance_results.get("findings", []),
                "quality_findings": quality_results.get("findings", [])
            }
            rewrite_results = self.rewriter_agent.execute(rewriter_task)
            
            # Step 6: Review Coordinator
            coordinator_task = {
                "code_analysis": code_analysis,
                "security_results": security_results,
                "performance_results": performance_results,
                "quality_results": quality_results,
                "rewrites": rewrite_results.get("rewrites", [])
            }
            summary = self.coordinator.execute(coordinator_task)
            
            return {
                "review_id": review_id,
                "status": "completed",
                "code_analysis": code_analysis,
                "security": security_results,
                "performance": performance_results,
                "quality": quality_results,
                "rewrites": rewrite_results.get("rewrites", []),
                "summary": summary
            }
        
        except Exception as e:
            return {
                "review_id": review_id,
                "status": "error",
                "error": str(e)
            }

