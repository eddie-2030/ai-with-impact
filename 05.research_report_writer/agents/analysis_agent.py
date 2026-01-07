# agents/analysis_agent.py
import json
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class AnalysisAgent(BaseAgent):
    """Agent responsible for analyzing findings and generating insights"""
    
    def __init__(self):
        super().__init__(
            name="analysis_agent",
            role="Data Analysis",
            allowed_tools=[]  # Analysis uses LLM primarily
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Analyze research findings"""
        findings = task.get("findings", [])
        query = task.get("query", "")
        
        # Prepare findings for analysis
        findings_text = "\n\n".join([
            f"Finding {i+1}: {f.get('content', '')}"
            for i, f in enumerate(findings)
        ])
        
        analysis_prompt = f"""Analyze the following research findings related to: {query}

Findings:
{findings_text}

Provide a JSON analysis with:
- key_insights: List of key insights from the findings
- patterns: List of patterns identified
- trends: List of trends observed
- connections: List of connections between findings
- gaps: List of gaps or areas needing more research

Return ONLY valid JSON."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You analyze research findings and identify patterns, insights, and connections. Return valid JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            return {
                "insights": analysis.get("key_insights", []),
                "patterns": analysis.get("patterns", []),
                "trends": analysis.get("trends", []),
                "connections": analysis.get("connections", []),
                "gaps": analysis.get("gaps", []),
                "status": "completed"
            }
        except Exception as e:
            return {
                "insights": [],
                "patterns": [],
                "trends": [],
                "connections": [],
                "gaps": [],
                "error": str(e),
                "status": "failed"
            }


