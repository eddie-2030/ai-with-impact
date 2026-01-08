# agents/performance_agent.py
from typing import Dict, Optional
from .base_agent import BaseAgent

class PerformanceAgent(BaseAgent):
    """Agent responsible for detecting performance issues"""
    
    def __init__(self):
        super().__init__(
            name="performance",
            role="Performance Analysis",
            allowed_tools=["performance_analyzer"]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Detect performance issues"""
        code = task.get("code", "")
        language = task.get("language", "python")
        
        # Use performance analyzer tool
        analysis_results = self.use_tool("performance_analyzer", code, language)
        
        # Generate LLM analysis if available
        analysis = self._generate_performance_analysis(code, analysis_results, language)
        
        return {
            "findings": analysis_results.get("findings", []),
            "total_findings": analysis_results.get("total_findings", 0),
            "critical_count": analysis_results.get("critical_count", 0),
            "high_count": analysis_results.get("high_count", 0),
            "medium_count": analysis_results.get("medium_count", 0),
            "low_count": analysis_results.get("low_count", 0),
            "analysis": analysis,
            "status": "completed"
        }
    
    def _generate_performance_analysis(self, code: str, analysis_results: Dict, language: str) -> str:
        """Generate performance analysis using LLM"""
        if not self.client:
            return "Performance analysis unavailable (LLM not configured)"
        
        findings = analysis_results.get("findings", [])
        if not findings:
            return "No significant performance issues detected. Code appears efficient."
        
        findings_summary = "\n".join([
            f"- {f['finding_type']} ({f['severity']}): {f.get('description', 'N/A')}"
            for f in findings[:5]
        ])
        
        analysis_prompt = f"""Analyze this {language} code for performance issues:

Code:
{code[:1000]}

Detected Issues:
{findings_summary}

Provide a brief performance analysis (2-3 sentences) explaining the issues and optimization opportunities."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a performance optimization expert. Provide concise, professional performance analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Performance analysis error: {str(e)}"

