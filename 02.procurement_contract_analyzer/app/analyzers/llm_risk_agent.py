from typing import List, Dict, Any, Optional
from app.adapters.llm_adapter import LLMAdapter
from app.models.schemas import ClauseComparison, AnalysisResult

class LLMRiskAgent:
    def __init__(self, llm_adapter: LLMAdapter):
        self.llm_adapter = llm_adapter
    
    def analyze_contract(self, contract_text: str, template_clauses: List[Dict], 
                        matched_clauses: List[Dict]) -> AnalysisResult:
        """Main method to analyze contract using LLM agent."""
        
        # Get comprehensive risk assessment from LLM
        risk_assessment = self.llm_adapter.assess_contract_risk(
            contract_text, template_clauses, matched_clauses
        )
        
        # Convert LLM assessment to our schema format
        clause_results = []
        missing_clauses = risk_assessment.get("missing_clauses", [])
        global_flags = risk_assessment.get("global_risks", [])
        
        # Process high-risk clauses
        for risk_clause in risk_assessment.get("high_risk_clauses", []):
            clause_comparison = ClauseComparison(
                clause_id=risk_clause.get("clause_title", "unknown"),
                title=risk_clause.get("clause_title", "Unknown Clause"),
                template_text="",  # Will be filled from template_clauses
                matched_text="",   # Will be filled from matched_clauses
                similarity=0.0,   # Will be calculated separately
                risk_flags=risk_clause.get("risk_factors", [])
            )
            clause_results.append(clause_comparison)
        
        # Process deviations
        for deviation in risk_assessment.get("deviations", []):
            clause_comparison = ClauseComparison(
                clause_id=deviation.get("clause_title", "unknown"),
                title=deviation.get("clause_title", "Unknown Clause"),
                template_text="",
                matched_text="",
                similarity=0.0,
                risk_flags=[f"{deviation.get('deviation_type', 'Unknown')}: {deviation.get('description', '')}"]
            )
            clause_results.append(clause_comparison)
        
        # Create analysis result
        result = AnalysisResult(
            template_name="llm_analyzed",
            overall_risk=risk_assessment.get("overall_risk_score", 50.0),
            risk_band=risk_assessment.get("risk_band", "MEDIUM"),
            missing_clauses=missing_clauses,
            clause_results=clause_results,
            global_flags=global_flags
        )
        
        return result
    
    def analyze_clause_similarity(self, template_clause: str, contract_clause: str) -> Dict[str, Any]:
        """Analyze similarity between template and contract clauses using LLM."""
        return self.llm_adapter.analyze_clause_similarity(template_clause, contract_clause)
    
    def get_risk_explanation(self, risk_score: float, risk_band: str) -> str:
        """Get human-readable explanation of risk assessment."""
        explanations = {
            "LOW": "Contract shows good alignment with standard template with minimal risks.",
            "MEDIUM": "Contract has some deviations and risks that require attention.",
            "HIGH": "Contract has significant risks and deviations that need immediate review."
        }
        
        base_explanation = explanations.get(risk_band, "Risk assessment completed.")
        
        if risk_score >= 80:
            return f"{base_explanation} High risk score ({risk_score:.1f}) indicates serious concerns."
        elif risk_score >= 60:
            return f"{base_explanation} Moderate risk score ({risk_score:.1f}) suggests careful review needed."
        else:
            return f"{base_explanation} Lower risk score ({risk_score:.1f}) indicates acceptable terms."
    
    def generate_recommendations(self, analysis_result: AnalysisResult) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        if analysis_result.overall_risk >= 80:
            recommendations.append("URGENT: High-risk contract requires immediate legal review")
            recommendations.append("Consider renegotiating key terms before signing")
        
        if analysis_result.missing_clauses:
            recommendations.append(f"Add missing critical clauses: {', '.join(analysis_result.missing_clauses[:3])}")
        
        if analysis_result.global_flags:
            recommendations.append("Address global risk factors identified in contract")
        
        if analysis_result.overall_risk >= 60:
            recommendations.append("Request contract modifications to reduce risk exposure")
            recommendations.append("Consider additional legal protections or insurance")
        
        if analysis_result.overall_risk < 40:
            recommendations.append("Contract appears acceptable with standard review")
        
        return recommendations
