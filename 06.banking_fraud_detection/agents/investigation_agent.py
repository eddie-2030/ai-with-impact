# agents/investigation_agent.py
import json
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class InvestigationAgent(BaseAgent):
    """Agent responsible for deep investigation of high-risk transactions"""
    
    def __init__(self):
        super().__init__(
            name="investigation",
            role="Fraud Investigation",
            allowed_tools=[]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Perform deep investigation"""
        transaction = task.get("transaction", {})
        risk_assessment = task.get("risk_assessment", {})
        user_history = task.get("user_history", [])
        
        # Gather additional context
        context_data = {
            "transaction_count_24h": self._count_recent_transactions(user_history, hours=24),
            "transaction_count_7d": self._count_recent_transactions(user_history, hours=168),
            "total_amount_24h": self._sum_recent_amounts(user_history, hours=24),
            "unique_locations_7d": len(set(t.get("location", "") for t in user_history if self._is_recent(t.get("timestamp"), hours=168))),
            "unique_devices_30d": len(set(t.get("device_id", "") for t in user_history if self._is_recent(t.get("timestamp"), hours=720)))
        }
        
        # Generate investigation report using LLM
        investigation_report = self._generate_investigation_report(
            transaction, risk_assessment, context_data
        )
        
        return {
            "context": context_data,
            "investigation_report": investigation_report,
            "recommendation": self._generate_recommendation(risk_assessment),
            "status": "completed"
        }
    
    def _count_recent_transactions(self, history: List[Dict], hours: int) -> int:
        """Count transactions within specified hours"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        count = 0
        for t in history:
            timestamp = t.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    if dt.replace(tzinfo=None) >= cutoff:
                        count += 1
                except:
                    pass
        return count
    
    def _sum_recent_amounts(self, history: List[Dict], hours: int) -> float:
        """Sum transaction amounts within specified hours"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        total = 0.0
        for t in history:
            timestamp = t.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    if dt.replace(tzinfo=None) >= cutoff:
                        total += float(t.get("amount", 0))
                except:
                    pass
        return total
    
    def _is_recent(self, timestamp, hours: int) -> bool:
        """Check if timestamp is within specified hours"""
        from datetime import datetime, timedelta
        if not timestamp:
            return False
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            return dt.replace(tzinfo=None) >= cutoff
        except:
            return False
    
    def _generate_investigation_report(self, transaction: Dict, risk_assessment: Dict,
                                       context: Dict) -> str:
        """Generate investigation report using LLM"""
        if not self.client:
            return "Investigation report unavailable (LLM not configured)"
        
        report_prompt = f"""Generate a fraud investigation report for this transaction:

Transaction Details:
- Amount: ${transaction.get('amount', 0)}
- Merchant: {transaction.get('merchant', 'Unknown')}
- Location: {transaction.get('location', 'Unknown')}
- Risk Score: {risk_assessment.get('risk_score', 0)}/100
- Risk Level: {risk_assessment.get('risk_level', 'low')}

Context:
- Transactions in last 24h: {context.get('transaction_count_24h', 0)}
- Total amount in last 24h: ${context.get('total_amount_24h', 0)}
- Unique locations in last 7d: {context.get('unique_locations_7d', 0)}
- Unique devices in last 30d: {context.get('unique_devices_30d', 0)}

Provide a concise investigation report (3-4 sentences) summarizing key findings and concerns."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a fraud investigation analyst. Provide professional, concise investigation reports."},
                    {"role": "user", "content": report_prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Investigation report error: {str(e)}"
    
    def _generate_recommendation(self, risk_assessment: Dict) -> str:
        """Generate investigation recommendation"""
        risk_level = risk_assessment.get("risk_level", "low")
        risk_score = risk_assessment.get("risk_score", 0.0)
        
        if risk_score >= 90:
            return "IMMEDIATE_REVIEW"
        elif risk_score >= 80:
            return "PRIORITY_REVIEW"
        elif risk_score >= 70:
            return "STANDARD_REVIEW"
        else:
            return "MONITOR"

