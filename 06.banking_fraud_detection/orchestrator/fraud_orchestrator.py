# orchestrator/fraud_orchestrator.py
import uuid
from typing import Dict, Optional, List
from datetime import datetime
from agents.transaction_monitor_agent import TransactionMonitorAgent
from agents.pattern_detection_agent import PatternDetectionAgent
from agents.risk_assessment_agent import RiskAssessmentAgent
from agents.investigation_agent import InvestigationAgent
from agents.alert_agent import AlertAgent

class FraudOrchestrator:
    """Orchestrates the multi-agent fraud detection workflow"""
    
    def __init__(self):
        self.monitor_agent = TransactionMonitorAgent()
        self.pattern_agent = PatternDetectionAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.investigation_agent = InvestigationAgent()
        self.alert_agent = AlertAgent()
    
    def process_transaction(self, transaction: Dict, user_history: Optional[List[Dict]] = None,
                           user_profile: Optional[Dict] = None,
                           min_risk_score: float = 70.0) -> Dict:
        """Process transaction through fraud detection workflow"""
        
        transaction_id = transaction.get("transaction_id", str(uuid.uuid4()))
        
        try:
            # Step 1: Transaction Monitor Agent
            monitor_task = {"transaction": transaction}
            monitor_result = self.monitor_agent.execute(monitor_task)
            
            # If basic validation fails, return early
            if monitor_result.get("suspicious_flags"):
                suspicious_flags = monitor_result.get("suspicious_flags", [])
                if "invalid_amount" in suspicious_flags:
                    return {
                        "transaction_id": transaction_id,
                        "status": "declined",
                        "reason": "Invalid transaction amount",
                        "risk_score": 100.0,
                        "risk_level": "critical"
                    }
            
            # Step 2: Pattern Detection Agent
            pattern_task = {
                "transaction": transaction,
                "user_history": user_history or []
            }
            pattern_result = self.pattern_agent.execute(pattern_task)
            
            # Step 3: Risk Assessment Agent
            risk_task = {
                "transaction": transaction,
                "pattern_results": pattern_result,
                "user_profile": user_profile or {}
            }
            risk_result = self.risk_agent.execute(risk_task)
            
            risk_score = risk_result.get("risk_score", 0.0)
            risk_level = risk_result.get("risk_level", "low")
            
            # Step 4: Investigation Agent (only if high risk)
            investigation_result = None
            if risk_score >= 70:
                investigation_task = {
                    "transaction": transaction,
                    "risk_assessment": risk_result,
                    "user_history": user_history or []
                }
                investigation_result = self.investigation_agent.execute(investigation_task)
            
            # Step 5: Alert Agent
            alert_task = {
                "transaction": transaction,
                "risk_assessment": risk_result,
                "pattern_results": pattern_result,
                "investigation": investigation_result or {}
            }
            alert_context = {"min_risk_score": min_risk_score}
            alert_result = self.alert_agent.execute(alert_task, alert_context)
            
            # Determine transaction status
            if risk_score >= 90:
                transaction_status = "flagged"
            elif risk_score >= 70:
                transaction_status = "review"
            else:
                transaction_status = "approved"
            
            return {
                "transaction_id": transaction_id,
                "status": transaction_status,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_result.get("risk_factors", {}),
                "patterns_detected": pattern_result.get("patterns_detected", []),
                "fraud_type": pattern_result.get("fraud_type", "none"),
                "alert": alert_result.get("alert") if alert_result.get("alert_generated") else None,
                "investigation": investigation_result,
                "analysis": risk_result.get("analysis", "")
            }
        
        except Exception as e:
            return {
                "transaction_id": transaction_id,
                "status": "error",
                "error": str(e),
                "risk_score": 0.0,
                "risk_level": "unknown"
            }

