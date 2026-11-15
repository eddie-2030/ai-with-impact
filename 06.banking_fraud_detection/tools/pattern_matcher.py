# tools/pattern_matcher.py
from typing import Dict, List, Optional
from .base_tool import BaseTool
from transaction_context import history_for_transaction, normalize_timestamp, within_window

class PatternMatcherTool(BaseTool):
    """Tool for matching transactions against fraud patterns"""
    
    def __init__(self):
        super().__init__(
            name="pattern_matcher",
            description="Match transactions against known fraud patterns"
        )
    
    def execute(self, transaction: Dict, user_history: Optional[List[Dict]] = None) -> Dict:
        """Check transaction against fraud patterns"""
        transaction = dict(transaction, timestamp=normalize_timestamp(transaction.get("timestamp")).isoformat())
        user_history = history_for_transaction(transaction, user_history)
        patterns_detected = []
        pattern_scores = {}
        
        # Pattern 1: Unusual Amount
        if self._check_unusual_amount(transaction, user_history):
            patterns_detected.append("unusual_amount")
            pattern_scores["unusual_amount"] = 0.7
        
        # Pattern 2: Geographic Anomaly
        if self._check_geographic_anomaly(transaction, user_history):
            patterns_detected.append("geographic_anomaly")
            pattern_scores["geographic_anomaly"] = 0.8
        
        # Pattern 3: Velocity Check (too many transactions quickly)
        if self._check_velocity(transaction, user_history):
            patterns_detected.append("high_velocity")
            pattern_scores["high_velocity"] = 0.6
        
        # Pattern 4: Unusual Merchant Category
        if self._check_merchant_anomaly(transaction, user_history):
            patterns_detected.append("unusual_merchant")
            pattern_scores["unusual_merchant"] = 0.5
        
        # Pattern 5: New Device
        if self._check_new_device(transaction, user_history):
            patterns_detected.append("new_device")
            pattern_scores["new_device"] = 0.6
        
        # Pattern 6: Off-Hours Transaction
        if self._check_off_hours(transaction):
            patterns_detected.append("off_hours")
            pattern_scores["off_hours"] = 0.4
        
        return {
            "patterns_detected": patterns_detected,
            "pattern_scores": pattern_scores,
            "total_pattern_score": sum(pattern_scores.values()) / len(pattern_scores) if pattern_scores else 0.0
        }
    
    def _check_unusual_amount(self, transaction: Dict, history: Optional[List[Dict]]) -> bool:
        """Check if transaction amount is unusual"""
        if not history:
            return False
        
        amounts = [float(t.get("amount", 0)) for t in history if t.get("amount")]
        if not amounts:
            return False
        
        avg_amount = sum(amounts) / len(amounts)
        current_amount = float(transaction.get("amount", 0))
        
        # Flag if amount is 3x average or more
        return current_amount > avg_amount * 3
    
    def _check_geographic_anomaly(self, transaction: Dict, history: Optional[List[Dict]]) -> bool:
        """Check if transaction location is unusual"""
        if not history:
            return False
        
        current_location = transaction.get("location", "")
        if not current_location:
            return False
        
        # Get recent locations (last 24 hours)
        recent_locations = [
            t.get("location", "") for t in history 
            if t.get("location") and self._is_recent(t.get("timestamp"), transaction.get("timestamp"))
        ]
        
        # If location not in recent locations, it's an anomaly
        return current_location not in recent_locations and len(recent_locations) > 0
    
    def _check_velocity(self, transaction: Dict, history: Optional[List[Dict]]) -> bool:
        """Check if too many transactions in short time"""
        if not history:
            return False
        
        # Count transactions in last hour
        recent_count = sum(
            1 for t in history 
            if self._is_within_hour(t.get("timestamp"), transaction.get("timestamp"))
        )
        
        # Flag if more than 5 transactions in last hour
        return recent_count > 5
    
    def _check_merchant_anomaly(self, transaction: Dict, history: Optional[List[Dict]]) -> bool:
        """Check if merchant category is unusual"""
        if not history:
            return False
        
        current_category = transaction.get("merchant_category", "")
        if not current_category:
            return False
        
        # Get typical merchant categories
        categories = [t.get("merchant_category", "") for t in history if t.get("merchant_category")]
        category_counts = {}
        for cat in categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # If current category never seen before, it's unusual
        return current_category not in category_counts
    
    def _check_new_device(self, transaction: Dict, history: Optional[List[Dict]]) -> bool:
        """Check if transaction is from a new device"""
        if not history:
            return False
        
        current_device = transaction.get("device_id", "")
        if not current_device:
            return False
        
        # Get known devices
        known_devices = set(t.get("device_id", "") for t in history if t.get("device_id"))
        
        # If device not in known devices, it's new
        return current_device not in known_devices and len(known_devices) > 0
    
    def _check_off_hours(self, transaction: Dict) -> bool:
        """Check if transaction is during off-hours"""
        dt = normalize_timestamp(transaction.get("timestamp"))
        hour = dt.hour
        # Off-hours: before 6 AM or after 11 PM
        return hour < 6 or hour > 23
    
    def _is_recent(self, timestamp, event_time) -> bool:
        """Check the 24 hours preceding this transaction's event time."""
        return within_window(timestamp, event_time, 86400)
    
    def _is_within_hour(self, timestamp1, timestamp2) -> bool:
        """Check the hour preceding the transaction, excluding future events."""
        return within_window(timestamp1, timestamp2, 3600)

