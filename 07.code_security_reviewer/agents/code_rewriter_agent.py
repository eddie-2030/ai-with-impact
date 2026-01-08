# agents/code_rewriter_agent.py
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class CodeRewriterAgent(BaseAgent):
    """Agent responsible for rewriting code to fix issues"""
    
    def __init__(self):
        super().__init__(
            name="code_rewriter",
            role="Code Rewriting",
            allowed_tools=[]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Rewrite code to fix issues"""
        code = task.get("code", "")
        language = task.get("language", "python")
        security_findings = task.get("security_findings", [])
        performance_findings = task.get("performance_findings", [])
        quality_findings = task.get("quality_findings", [])
        
        all_findings = security_findings + performance_findings + quality_findings
        
        if not all_findings:
            return {
                "rewrites": [],
                "status": "completed",
                "message": "No issues found to rewrite"
            }
        
        # Generate rewrites for each finding
        rewrites = []
        for finding in all_findings:
            rewrite = self._generate_rewrite(code, finding, language)
            if rewrite:
                rewrites.append(rewrite)
        
        return {
            "rewrites": rewrites,
            "total_rewrites": len(rewrites),
            "status": "completed"
        }
    
    def _generate_rewrite(self, code: str, finding: Dict, language: str) -> Optional[Dict]:
        """Generate rewritten code for a specific finding"""
        if not self.client:
            return None
        
        finding_type = finding.get("finding_type", "")
        severity = finding.get("severity", "medium")
        code_snippet = finding.get("code_snippet", "")
        line_number = finding.get("line_number", 0)
        description = finding.get("description", "")
        
        # Determine confidence based on finding type and severity
        confidence = self._calculate_confidence(finding_type, severity)
        
        # Determine rewrite mode
        if confidence >= 90:
            rewrite_mode = "auto_apply"
        elif confidence >= 70:
            rewrite_mode = "suggest"
        else:
            rewrite_mode = "review"
        
        rewrite_prompt = f"""Rewrite this {language} code to fix the following issue:

Issue Type: {finding_type}
Severity: {severity}
Description: {description}
Line Number: {line_number}

Original Code:
{code_snippet}

Context (surrounding code):
{self._get_context(code, line_number)}

Please provide:
1. The rewritten code that fixes the issue
2. A brief explanation of what was changed and why

Return the response in this format:
REWRITTEN_CODE:
[the fixed code]

EXPLANATION:
[explanation of changes]"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are an expert {language} developer. Fix code issues while preserving functionality."},
                    {"role": "user", "content": rewrite_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content
            
            # Parse response
            rewritten_code, explanation = self._parse_rewrite_response(response_text, code_snippet)
            
            if rewritten_code:
                return {
                    "finding_id": finding.get("id"),
                    "finding_type": finding_type,
                    "original_code": code_snippet,
                    "rewritten_code": rewritten_code,
                    "explanation": explanation,
                    "confidence_score": confidence,
                    "rewrite_mode": rewrite_mode,
                    "line_number": line_number
                }
        except Exception as e:
            return None
        
        return None
    
    def _calculate_confidence(self, finding_type: str, severity: str) -> float:
        """Calculate confidence score for rewrite"""
        base_confidence = {
            "sql_injection": 95.0,
            "hardcoded_secret": 98.0,
            "n_plus_one": 90.0,
            "nested_loop": 85.0,
            "missing_index": 70.0,
            "long_function": 60.0
        }
        
        confidence = base_confidence.get(finding_type, 70.0)
        
        # Adjust based on severity
        if severity == "critical":
            confidence += 5.0
        elif severity == "high":
            confidence += 3.0
        elif severity == "low":
            confidence -= 5.0
        
        return min(100.0, max(0.0, confidence))
    
    def _get_context(self, code: str, line_number: int, context_lines: int = 5) -> str:
        """Get context around a line number"""
        lines = code.split('\n')
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        return '\n'.join(lines[start:end])
    
    def _parse_rewrite_response(self, response: str, original_code: str) -> tuple:
        """Parse LLM response to extract rewritten code and explanation"""
        rewritten_code = original_code  # Default fallback
        explanation = "Code rewrite generated"
        
        # Try to extract from structured format
        if "REWRITTEN_CODE:" in response:
            parts = response.split("REWRITTEN_CODE:")
            if len(parts) > 1:
                code_part = parts[1].split("EXPLANATION:")[0].strip()
                rewritten_code = code_part.strip('```').strip()
        
        if "EXPLANATION:" in response:
            parts = response.split("EXPLANATION:")
            if len(parts) > 1:
                explanation = parts[1].strip()
        
        return rewritten_code, explanation

