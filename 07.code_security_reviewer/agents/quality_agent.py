# agents/quality_agent.py
from typing import Dict, Optional
from .base_agent import BaseAgent

class QualityAgent(BaseAgent):
    """Agent responsible for checking code quality"""
    
    def __init__(self):
        super().__init__(
            name="quality",
            role="Code Quality Analysis",
            allowed_tools=[]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Check code quality"""
        code = task.get("code", "")
        language = task.get("language", "python")
        
        # Basic quality checks
        findings = self._check_quality(code, language)
        
        # Generate LLM analysis if available
        analysis = self._generate_quality_analysis(code, findings, language)
        
        return {
            "findings": findings,
            "total_findings": len(findings),
            "analysis": analysis,
            "status": "completed"
        }
    
    def _check_quality(self, code: str, language: str) -> list:
        """Perform quality checks"""
        findings = []
        lines = code.split('\n')
        
        # Check for long functions (Python)
        if language.lower() == "python":
            # Simple heuristic: functions with many lines
            in_function = False
            function_lines = 0
            function_start = 0
            
            for line_num, line in enumerate(lines, 1):
                if line.strip().startswith('def '):
                    if in_function and function_lines > 50:
                        findings.append({
                            "finding_type": "long_function",
                            "severity": "medium",
                            "description": f"Function is {function_lines} lines long (consider breaking into smaller functions)",
                            "line_number": function_start,
                            "code_snippet": lines[function_start-1].strip() if function_start > 0 else "",
                            "metric_value": function_lines,
                            "confidence_score": 75.0
                        })
                    in_function = True
                    function_lines = 0
                    function_start = line_num
                elif line.strip().startswith('class ') or (line.strip() and not line.startswith(' ') and not line.startswith('\t')):
                    in_function = False
                elif in_function:
                    function_lines += 1
        
        # Check for code duplication (simple heuristic)
        # This is simplified - in production, use more sophisticated tools
        
        return findings
    
    def _generate_quality_analysis(self, code: str, findings: list, language: str) -> str:
        """Generate quality analysis using LLM"""
        if not self.client:
            return "Quality analysis unavailable (LLM not configured)"
        
        if not findings:
            return "Code quality is good. No significant issues detected."
        
        findings_summary = "\n".join([
            f"- {f['finding_type']} ({f['severity']}): {f.get('description', 'N/A')}"
            for f in findings[:5]
        ])
        
        analysis_prompt = f"""Analyze this {language} code for quality issues:

Code:
{code[:1000]}

Detected Issues:
{findings_summary}

Provide a brief code quality analysis (2-3 sentences) with recommendations."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a code quality expert. Provide concise, professional quality analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Quality analysis error: {str(e)}"

