# agents/investigation_agent.py
import json
from typing import Dict, List, Optional
from .base_agent import BaseAgent
from transaction_context import history_for_transaction, normalize_timestamp, within_window

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
        event_time = normalize_timestamp(transaction.get("timestamp"))
        transaction = dict(transaction, timestamp=event_time.isoformat())
        risk_assessment = task.get("risk_assessment", {})
        user_history = history_for_transaction(transaction, task.get("user_history", []))
        
        # Gather additional context
        context_data = {
            "transaction_count_24h": self._count_recent_transactions(user_history, hours=24, event_time=event_time),
            "transaction_count_7d": self._count_recent_transactions(user_history, hours=168, event_time=event_time),
            "total_amount_24h": self._sum_recent_amounts(user_history, hours=24, event_time=event_time),
            "unique_locations_7d": len(set(t.get("location", "") for t in user_history if self._is_recent(t.get("timestamp"), hours=168, event_time=event_time))),
            "unique_devices_30d": len(set(t.get("device_id", "") for t in user_history if self._is_recent(t.get("timestamp"), hours=720, event_time=event_time)))
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
    
    def _count_recent_transactions(self, history: List[Dict], hours: int, event_time) -> int:
        """Count transactions within specified hours"""
        return sum(self._is_recent(t.get("timestamp"), hours, event_time) for t in history)
    
    def _sum_recent_amounts(self, history: List[Dict], hours: int, event_time) -> float:
        """Sum transaction amounts within specified hours"""
        return sum(float(t.get("amount", 0)) for t in history
                   if self._is_recent(t.get("timestamp"), hours, event_time))
    
    def _is_recent(self, timestamp, hours: int, event_time) -> bool:
        """Check if timestamp is within specified hours"""
        return within_window(timestamp, event_time, hours * 3600, include_cutoff=True)
    
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
            return response.choices[0].message.content or "Investigation report unavailable"
        except Exception:
            return "Investigation report unavailable from the model provider"
    
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

