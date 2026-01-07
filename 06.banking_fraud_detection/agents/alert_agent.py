# agents/alert_agent.py
import uuid
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class AlertAgent(BaseAgent):
    """Agent responsible for generating and managing fraud alerts"""
    
    def __init__(self):
        super().__init__(
            name="alert",
            role="Alert Generation",
            allowed_tools=[]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Generate fraud alert"""
        transaction = task.get("transaction", {})
        risk_assessment = task.get("risk_assessment", {})
        pattern_results = task.get("pattern_results", {})
        investigation = task.get("investigation", {})
        
        risk_score = risk_assessment.get("risk_score", 0.0)
        risk_level = risk_assessment.get("risk_level", "low")
        
        # Determine if alert should be generated
        min_risk_score = float(context.get("min_risk_score", 70) if context else 70)
        
        if risk_score < min_risk_score:
            return {
                "alert_generated": False,
                "reason": f"Risk score {risk_score} below threshold {min_risk_score}",
                "status": "completed"
            }
        
        # Determine severity
        if risk_score >= 90:
            severity = "critical"
        elif risk_score >= 80:
            severity = "high"
        elif risk_score >= 70:
            severity = "medium"
        else:
            severity = "low"
        
        # Determine alert type
        fraud_type = pattern_results.get("fraud_type", "suspicious_activity")
        
        # Generate alert description
        description = self._generate_alert_description(
            transaction, risk_assessment, pattern_results, fraud_type
        )
        
        alert = {
            "alert_id": str(uuid.uuid4()),
            "transaction_id": transaction.get("transaction_id", ""),
            "user_id": transaction.get("user_id", ""),
            "alert_type": fraud_type,
            "severity": severity,
            "risk_score": risk_score,
            "description": description,
            "patterns_detected": pattern_results.get("patterns_detected", []),
            "investigation_recommendation": investigation.get("recommendation", "MONITOR")
        }
        
        return {
            "alert_generated": True,
            "alert": alert,
            "status": "completed"
        }
    
    def _generate_alert_description(self, transaction: Dict, risk_assessment: Dict,
                                   pattern_results: Dict, fraud_type: str) -> str:
        """Generate alert description"""
        patterns = pattern_results.get("patterns_detected", [])
        risk_score = risk_assessment.get("risk_score", 0.0)
        
        description = f"Fraud alert: {fraud_type.replace('_', ' ').title()}\n"
        description += f"Risk Score: {risk_score}/100\n"
        description += f"Transaction: ${transaction.get('amount', 0)} at {transaction.get('merchant', 'Unknown')}\n"
        description += f"Detected Patterns: {', '.join(patterns) if patterns else 'None'}\n"
        description += f"Location: {transaction.get('location', 'Unknown')}"
        
        return description

