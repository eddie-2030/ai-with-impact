# tools/risk_calculator.py
from typing import Dict, List, Optional
from .base_tool import BaseTool

class RiskCalculatorTool(BaseTool):
    """Tool for calculating fraud risk scores"""
    
    def __init__(self):
        super().__init__(
            name="risk_calculator",
            description="Calculate composite fraud risk scores"
        )
    
    def execute(self, transaction: Dict, pattern_results: Dict, 
                user_profile: Optional[Dict] = None) -> Dict:
        """Calculate composite risk score"""
        
        risk_factors = {}
        total_score = 0.0
        
        # Factor 1: Pattern matches (weight: 40%)
        pattern_score = pattern_results.get("total_pattern_score", 0.0) * 100
        risk_factors["pattern_matching"] = {
            "score": pattern_score,
            "weight": 0.4,
            "contribution": pattern_score * 0.4
        }
        total_score += pattern_score * 0.4
        
        # Factor 2: Transaction amount (weight: 20%)
        amount = float(transaction.get("amount", 0))
        amount_score = min(amount / 10000 * 100, 100)  # Normalize to 0-100
        risk_factors["amount"] = {
            "score": amount_score,
            "weight": 0.2,
            "contribution": amount_score * 0.2
        }
        total_score += amount_score * 0.2
        
        # Factor 3: User risk profile (weight: 15%)
        user_risk = user_profile.get("risk_profile", "low") if user_profile else "low"
        user_risk_scores = {"low": 20, "medium": 50, "high": 80}
        user_score = user_risk_scores.get(user_risk, 20)
        risk_factors["user_profile"] = {
            "score": user_score,
            "weight": 0.15,
            "contribution": user_score * 0.15
        }
        total_score += user_score * 0.15
        
        # Factor 4: Device/IP risk (weight: 15%)
        device_risk = 0.0
        if transaction.get("device_id"):
            # New device adds risk
            if pattern_results.get("patterns_detected", []):
                if "new_device" in pattern_results["patterns_detected"]:
                    device_risk = 70.0
        risk_factors["device"] = {
            "score": device_risk,
            "weight": 0.15,
            "contribution": device_risk * 0.15
        }
        total_score += device_risk * 0.15
        
        # Factor 5: Time-based risk (weight: 10%)
        time_risk = 0.0
        if "off_hours" in pattern_results.get("patterns_detected", []):
            time_risk = 50.0
        risk_factors["time"] = {
            "score": time_risk,
            "weight": 0.1,
            "contribution": time_risk * 0.1
        }
        total_score += time_risk * 0.1
        
        # Determine risk level
        if total_score >= 90:
            risk_level = "critical"
        elif total_score >= 80:
            risk_level = "high"
        elif total_score >= 70:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_score": round(total_score, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors
        }

