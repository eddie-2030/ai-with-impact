# agents/security_agent.py
from typing import Dict, Optional
from .base_agent import BaseAgent

class SecurityAgent(BaseAgent):
    """Agent responsible for detecting security vulnerabilities"""
    
    def __init__(self):
        super().__init__(
            name="security",
            role="Security Vulnerability Detection",
            allowed_tools=["security_scanner"]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Detect security vulnerabilities"""
        code = task.get("code", "")
        language = task.get("language", "python")
        
        # Use security scanner tool
        scan_results = self.use_tool("security_scanner", code, language)
        
        # Generate LLM analysis if available
        analysis = self._generate_security_analysis(code, scan_results, language)
        
        return {
            "findings": scan_results.get("findings", []),
            "total_findings": scan_results.get("total_findings", 0),
            "critical_count": scan_results.get("critical_count", 0),
            "high_count": scan_results.get("high_count", 0),
            "medium_count": scan_results.get("medium_count", 0),
            "low_count": scan_results.get("low_count", 0),
            "analysis": analysis,
            "status": "completed"
        }
    
    def _generate_security_analysis(self, code: str, scan_results: Dict, language: str) -> str:
        """Generate security analysis using LLM"""
        if not self.client:
            return "Security analysis unavailable (LLM not configured)"
        
        findings = scan_results.get("findings", [])
        if not findings:
            return "No security vulnerabilities detected. Code appears secure."
        
        findings_summary = "\n".join([
            f"- {f['finding_type']} ({f['severity']}): {f['description']}"
            for f in findings[:5]
        ])
        
        analysis_prompt = f"""Analyze this {language} code for security vulnerabilities:

Code:
{code[:1000]}

Detected Issues:
{findings_summary}

Provide a brief security analysis (2-3 sentences) explaining the vulnerabilities and their impact."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a security expert. Provide concise, professional security analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Security analysis error: {str(e)}"

