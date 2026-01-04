# agents/synthesis_agent.py
import json
from typing import Dict, List, Optional
from .base_agent import BaseAgent
from tools.tool_registry import tool_registry

class SynthesisAgent(BaseAgent):
    """Agent responsible for synthesizing findings into a comprehensive report"""
    
    def __init__(self):
        super().__init__(
            name="synthesis_agent",
            role="Report Synthesis",
            allowed_tools=["format_apa_citation"]
        )
        self.citation_formatter = tool_registry.get_tool("format_apa_citation")
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Synthesize findings into a report"""
        findings = task.get("findings", [])
        sources = task.get("sources", [])
        analysis = task.get("analysis", {})
        query = task.get("query", "")
        
        # Filter sources by credibility (use verified sources only)
        min_credibility = float(context.get("min_credibility_score", 0.6) if context else 0.6)
        verified_sources = [
            s for s in sources 
            if s.get("credibility_score", 0) >= min_credibility
        ]
        verified_source_ids = {s["source_id"] for s in verified_sources}
        
        # Filter findings to only use verified sources
        verified_findings = [
            f for f in findings 
            if f.get("source_id") in verified_source_ids
        ]
        
        # Generate report using LLM
        findings_text = "\n\n".join([
            f"• {f.get('content', '')} (Source: {f.get('source_id', 'unknown')})"
            for f in verified_findings
        ])
        
        insights_text = "\n".join([f"• {insight}" for insight in analysis.get("insights", [])])
        
        report_prompt = f"""Create a comprehensive research report on: {query}

Key Findings:
{findings_text}

Key Insights:
{insights_text}

Create a well-structured research report in Markdown format with the following sections:
1. Executive Summary (2-3 sentences)
2. Introduction
3. Key Findings (with in-text citations in APA format: (Author, Year))
4. Analysis & Insights
5. Conclusion

Use in-text citations like (Author, Year) throughout. Be thorough and professional.

Return ONLY the markdown report, no additional text."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You write comprehensive, well-structured research reports with proper citations. Return markdown only."},
                    {"role": "user", "content": report_prompt}
                ],
                temperature=0.3,
            )
            
            report_content = response.choices[0].message.content
            
            # Generate APA reference list
            references = self.citation_formatter.format_reference_list(verified_sources)
            
            # Generate in-text citations for findings
            source_map = {s["source_id"]: s for s in verified_sources}
            for finding in verified_findings:
                source_id = finding.get("source_id")
                source = source_map.get(source_id, {})
                if source:
                    citation = self.citation_formatter.generate_in_text_citation(
                        source, 
                        finding.get("page_number")
                    )
                    finding["in_text_citation"] = citation
            
            # Extract executive summary (first paragraph)
            executive_summary = report_content.split("\n\n")[0] if report_content else ""
            
            return {
                "report_content": report_content,
                "executive_summary": executive_summary,
                "references": references,
                "word_count": len(report_content.split()),
                "source_count": len(verified_sources),
                "status": "completed"
            }
        except Exception as e:
            return {
                "report_content": f"Error generating report: {str(e)}",
                "executive_summary": "",
                "references": "",
                "word_count": 0,
                "source_count": 0,
                "error": str(e),
                "status": "failed"
            }

