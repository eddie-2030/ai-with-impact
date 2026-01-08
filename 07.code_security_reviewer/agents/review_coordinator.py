# agents/review_coordinator.py
from typing import Dict, Optional
from .base_agent import BaseAgent

class ReviewCoordinator(BaseAgent):
    """Agent responsible for coordinating review and generating summary"""
    
    def __init__(self):
        super().__init__(
            name="review_coordinator",
            role="Review Coordination",
            allowed_tools=[]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Coordinate review and generate summary"""
        code_analysis = task.get("code_analysis", {})
        security_results = task.get("security_results", {})
        performance_results = task.get("performance_results", {})
        quality_results = task.get("quality_results", {})
        rewrites = task.get("rewrites", [])
        
        # Calculate scores
        security_score = self._calculate_security_score(security_results)
        performance_score = self._calculate_performance_score(performance_results)
        quality_score = self._calculate_quality_score(quality_results)
        overall_score = (security_score + performance_score + quality_score) / 3
        
        # Count findings by severity
        all_findings = (
            security_results.get("findings", []) +
            performance_results.get("findings", []) +
            quality_results.get("findings", [])
        )
        
        critical_count = sum(1 for f in all_findings if f.get("severity") == "critical")
        high_count = sum(1 for f in all_findings if f.get("severity") == "high")
        medium_count = sum(1 for f in all_findings if f.get("severity") == "medium")
        low_count = sum(1 for f in all_findings if f.get("severity") == "low")
        
        # Generate summary
        summary = self._generate_summary(
            security_results, performance_results, quality_results, rewrites
        )
        
        recommendations = self._generate_recommendations(
            security_results, performance_results, quality_results
        )
        
        return {
            "security_score": security_score,
            "performance_score": performance_score,
            "quality_score": quality_score,
            "overall_score": overall_score,
            "total_findings": len(all_findings),
            "critical_findings": critical_count,
            "high_findings": high_count,
            "medium_findings": medium_count,
            "low_findings": low_count,
            "summary": summary,
            "recommendations": recommendations,
            "status": "completed"
        }
    
    def _calculate_security_score(self, security_results: Dict) -> float:
        """Calculate security score (0-100)"""
        findings = security_results.get("findings", [])
        if not findings:
            return 100.0
        
        # Deduct points based on severity
        score = 100.0
        for finding in findings:
            severity = finding.get("severity", "medium")
            if severity == "critical":
                score -= 20
            elif severity == "high":
                score -= 15
            elif severity == "medium":
                score -= 10
            elif severity == "low":
                score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _calculate_performance_score(self, performance_results: Dict) -> float:
        """Calculate performance score (0-100)"""
        findings = performance_results.get("findings", [])
        if not findings:
            return 100.0
        
        score = 100.0
        for finding in findings:
            severity = finding.get("severity", "medium")
            if severity == "critical":
                score -= 15
            elif severity == "high":
                score -= 12
            elif severity == "medium":
                score -= 8
            elif severity == "low":
                score -= 4
        
        return max(0.0, min(100.0, score))
    
    def _calculate_quality_score(self, quality_results: Dict) -> float:
        """Calculate quality score (0-100)"""
        findings = quality_results.get("findings", [])
        if not findings:
            return 100.0
        
        score = 100.0
        for finding in findings:
            severity = finding.get("severity", "medium")
            if severity == "critical":
                score -= 10
            elif severity == "high":
                score -= 8
            elif severity == "medium":
                score -= 5
            elif severity == "low":
                score -= 2
        
        return max(0.0, min(100.0, score))
    
    def _generate_summary(self, security_results: Dict, performance_results: Dict,
                         quality_results: Dict, rewrites: List[Dict]) -> str:
        """Generate review summary"""
        if not self.client:
            return "Review summary unavailable (LLM not configured)"
        
        summary_prompt = f"""Generate a concise code review summary:

Security Findings: {len(security_results.get('findings', []))} issues
Performance Findings: {len(performance_results.get('findings', []))} issues
Quality Findings: {len(quality_results.get('findings', []))} issues
Code Rewrites Generated: {len(rewrites)}

Provide a brief 2-3 sentence summary of the code review results."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a code review coordinator. Provide concise, professional summaries."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Summary generation error: {str(e)}"
    
    def _generate_recommendations(self, security_results: Dict, performance_results: Dict,
                                  quality_results: Dict) -> str:
        """Generate recommendations"""
        recommendations = []
        
        if security_results.get("findings"):
            recommendations.append("Address security vulnerabilities immediately, especially critical issues.")
        
        if performance_results.get("findings"):
            recommendations.append("Optimize performance bottlenecks to improve efficiency.")
        
        if quality_results.get("findings"):
            recommendations.append("Improve code quality and maintainability.")
        
        if not recommendations:
            return "Code is in good shape. Continue following best practices."
        
        return " ".join(recommendations)

