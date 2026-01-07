# agents/pattern_detection_agent.py
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class PatternDetectionAgent(BaseAgent):
    """Agent responsible for detecting fraud patterns"""
    
    def __init__(self):
        super().__init__(
            name="pattern_detection",
            role="Fraud Pattern Detection",
            allowed_tools=["pattern_matcher"]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Detect fraud patterns in transaction"""
        transaction = task.get("transaction", {})
        user_history = task.get("user_history", [])
        
        # Use pattern matcher tool
        pattern_results = self.use_tool("pattern_matcher", transaction, user_history)
        
        # Determine fraud type based on patterns
        fraud_type = self._determine_fraud_type(pattern_results)
        
        return {
            "patterns_detected": pattern_results.get("patterns_detected", []),
            "pattern_scores": pattern_results.get("pattern_scores", {}),
            "total_pattern_score": pattern_results.get("total_pattern_score", 0.0),
            "fraud_type": fraud_type,
            "status": "completed"
        }
    
    def _determine_fraud_type(self, pattern_results: Dict) -> str:
        """Determine fraud type based on detected patterns"""
        patterns = pattern_results.get("patterns_detected", [])
        
        if "geographic_anomaly" in patterns and "new_device" in patterns:
            return "account_takeover"
        elif "unusual_amount" in patterns and "high_velocity" in patterns:
            return "card_fraud"
        elif "high_velocity" in patterns and len(patterns) >= 3:
            return "money_laundering"
        elif "unusual_merchant" in patterns and "off_hours" in patterns:
            return "suspicious_activity"
        elif len(patterns) >= 2:
            return "suspicious_activity"
        else:
            return "none"

