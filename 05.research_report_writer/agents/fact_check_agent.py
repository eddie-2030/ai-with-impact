# agents/fact_check_agent.py
import json
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class FactCheckAgent(BaseAgent):
    """Agent responsible for verifying source credibility and fact-checking"""
    
    def __init__(self):
        super().__init__(
            name="fact_check_agent",
            role="Source Verification",
            allowed_tools=["web_search"]  # For cross-referencing
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Verify sources and check facts"""
        sources = task.get("sources", [])
        findings = task.get("findings", [])
        
        verifications = []
        
        for source in sources:
            source_id = source.get("source_id")
            url = source.get("url", "")
            
            # Basic credibility scoring
            credibility_score = self._calculate_credibility_score(source)
            
            # Check URL validity (simplified - in production, actually check)
            url_valid = bool(url and url.startswith("http"))
            
            # Determine verification status
            if credibility_score >= 0.8:
                status = "verified"
            elif credibility_score >= 0.6:
                status = "questionable"
            else:
                status = "unreliable"
            
            verification = {
                "source_id": source_id,
                "credibility_score": credibility_score,
                "verification_status": status,
                "url_valid": url_valid,
                "domain_reputation": self._assess_domain_reputation(url),
                "peer_reviewed": source.get("source_type") == "academic_paper",
                "cross_reference_count": 0,  # Would be calculated with actual cross-referencing
                "consensus_level": "medium"  # Would be calculated
            }
            
            verifications.append(verification)
        
        return {
            "verifications": verifications,
            "status": "completed"
        }
    
    def _calculate_credibility_score(self, source: Dict) -> float:
        """Calculate credibility score for a source"""
        score = 0.5  # Base score
        
        source_type = source.get("source_type", "website")
        if source_type == "academic_paper":
            score += 0.3
        elif source_type == "news_article":
            score += 0.2
        elif source_type == "report":
            score += 0.15
        
        # Check if has DOI (academic papers)
        if source.get("doi"):
            score += 0.1
        
        # Check if has authors
        if source.get("authors"):
            score += 0.1
        
        # Check publisher reputation (simplified)
        publisher = source.get("publisher", "").lower()
        if any(reputable in publisher for reputable in ["university", "journal", "research", "edu"]):
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_domain_reputation(self, url: str) -> str:
        """Assess domain reputation (simplified)"""
        if not url:
            return "unknown"
        
        domain = url.split("/")[2] if len(url.split("/")) > 2 else url
        domain_lower = domain.lower()
        
        # Simple reputation check
        if any(edu in domain_lower for edu in [".edu", ".ac.", "university"]):
            return "high"
        elif any(gov in domain_lower for gov in [".gov", ".org"]):
            return "high"
        elif any(news in domain_lower for news in ["news", "reuters", "bbc"]):
            return "medium"
        else:
            return "medium"

