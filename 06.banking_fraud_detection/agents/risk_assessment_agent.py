# agents/risk_assessment_agent.py
import json
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class RiskAssessmentAgent(BaseAgent):
    """Agent responsible for assessing fraud risk"""
    
    def __init__(self):
        super().__init__(
            name="risk_assessment",
            role="Risk Assessment",
            allowed_tools=["risk_calculator"]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Assess fraud risk for transaction"""
        transaction = task.get("transaction", {})
        pattern_results = task.get("pattern_results", {})
        user_profile = task.get("user_profile", {})
        
        # Calculate risk score using tool
        risk_result = self.use_tool("risk_calculator", transaction, pattern_results, user_profile)
        
        # Generate LLM analysis if available
        analysis = self._generate_risk_analysis(transaction, risk_result, pattern_results)
        
        return {
            "risk_score": risk_result.get("risk_score", 0.0),
            "risk_level": risk_result.get("risk_level", "low"),
            "risk_factors": risk_result.get("risk_factors", {}),
            "analysis": analysis,
            "status": "completed"
        }
    
    def _generate_risk_analysis(self, transaction: Dict, risk_result: Dict, 
                                pattern_results: Dict) -> str:
        """Generate risk analysis using LLM"""
        if not self.client:
            return "Risk analysis unavailable (LLM not configured)"
        
        patterns = pattern_results.get("patterns_detected", [])
        risk_score = risk_result.get("risk_score", 0.0)
        risk_level = risk_result.get("risk_level", "low")
        
        analysis_prompt = f"""Analyze this transaction for fraud risk:

Transaction:
- Amount: ${transaction.get('amount', 0)}
- Merchant: {transaction.get('merchant', 'Unknown')}
- Location: {transaction.get('location', 'Unknown')}
- Type: {transaction.get('transaction_type', 'Unknown')}

Detected Patterns: {', '.join(patterns) if patterns else 'None'}
Risk Score: {risk_score}/100
Risk Level: {risk_level}

Provide a brief risk analysis (2-3 sentences) explaining why this transaction is flagged and what factors contribute to the risk score."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a fraud detection analyst. Provide concise, professional risk analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Risk analysis error: {str(e)}"

