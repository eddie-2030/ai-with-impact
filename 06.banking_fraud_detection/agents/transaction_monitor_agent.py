# agents/transaction_monitor_agent.py
from typing import Dict, List, Optional
from .base_agent import BaseAgent
from datetime import datetime

class TransactionMonitorAgent(BaseAgent):
    """Agent responsible for monitoring transactions and extracting features"""
    
    def __init__(self):
        super().__init__(
            name="transaction_monitor",
            role="Transaction Monitoring",
            allowed_tools=[]
        )
    
    def execute(self, task: Dict, context: Optional[Dict] = None) -> Dict:
        """Monitor transaction and extract features"""
        transaction = task.get("transaction", {})
        
        # Extract features
        features = {
            "amount": float(transaction.get("amount", 0)),
            "merchant": transaction.get("merchant", ""),
            "merchant_category": transaction.get("merchant_category", ""),
            "location": transaction.get("location", ""),
            "device_id": transaction.get("device_id", ""),
            "ip_address": transaction.get("ip_address", ""),
            "transaction_type": transaction.get("transaction_type", ""),
            "payment_method": transaction.get("payment_method", ""),
            "timestamp": transaction.get("timestamp", ""),
            "is_weekend": self._is_weekend(transaction.get("timestamp")),
            "is_off_hours": self._is_off_hours(transaction.get("timestamp"))
        }
        
        # Basic validation
        suspicious_flags = []
        if features["amount"] <= 0:
            suspicious_flags.append("invalid_amount")
        if not features["merchant"]:
            suspicious_flags.append("missing_merchant")
        if not features["location"]:
            suspicious_flags.append("missing_location")
        
        return {
            "features": features,
            "suspicious_flags": suspicious_flags,
            "status": "monitored"
        }
    
    def _is_weekend(self, timestamp) -> bool:
        """Check if timestamp is on weekend"""
        if not timestamp:
            return False
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            return dt.weekday() >= 5  # Saturday = 5, Sunday = 6
        except:
            return False
    
    def _is_off_hours(self, timestamp) -> bool:
        """Check if timestamp is during off-hours"""
        if not timestamp:
            return False
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            hour = dt.hour
            return hour < 6 or hour > 23
        except:
            return False

