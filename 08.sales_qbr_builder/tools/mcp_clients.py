# tools/mcp_clients.py
"""
MCP (Model Context Protocol) clients for fetching data from external systems.
In production, these would connect to real MCP servers for CRM, Analytics, and Support.
For now, these are mock implementations that return sample data.
"""
from __future__ import annotations
from typing import Dict, Any
from datetime import date
from typing import Tuple

def _scenario(account_id: str) -> str:
    """
    Deterministic scenario selector so you can drive wins/risks from the Streamlit UI
    just by changing the Account ID.
    """
    aid = (account_id or "").lower()
    if "mixed" in aid:
        return "mixed"   # wins + risks
    if "risk" in aid:
        return "risk"    # mostly risks
    if "win" in aid:
        return "win"     # mostly wins
    return "default"

def fetch_crm_data(account_id: str, period_start: date, period_end: date) -> Dict[str, Any]:
    """
    Fetch CRM data from MCP server (read-only)
    In production, this would connect to a real CRM MCP server (Salesforce, HubSpot, etc.)
    """
    scen = _scenario(account_id)
    if scen == "risk":
        renewal_probability = 0.62
        opps = []
    elif scen == "mixed":
        renewal_probability = 0.66
        opps = [
            {"name": "Targeted Expansion", "value": 75000, "stage": "Discovery", "close_date": "2025-05-30"}
        ]
    elif scen == "win":
        renewal_probability = 0.92
        opps = [
            {"name": "Expansion (High Intent)", "value": 150000, "stage": "Negotiation", "close_date": "2025-06-15"}
        ]
    else:
        renewal_probability = 0.85
        opps = [
            {"name": "Q2 Expansion", "value": 100000, "stage": "Negotiation", "close_date": "2025-06-30"}
        ]

    # Mock CRM data - replace with real MCP client call
    return {
        "account_id": account_id,
        "account_name": "Acme Corp",
        "industry": "Technology",
        "segment": "Enterprise",
        "contract_value": 500000,
        "arr": 480000,
        "mrr": 40000,
        "renewal_date": "2025-12-31",
        "renewal_probability": renewal_probability,
        "opportunities": opps,
        "key_stakeholders": [
            {"name": "John Doe", "role": "CTO", "influence": "high"},
            {"name": "Jane Smith", "role": "VP Engineering", "influence": "medium"}
        ]
    }

def fetch_analytics_data(account_id: str, period_start: date, period_end: date) -> Dict[str, Any]:
    """
    Fetch product analytics data from MCP server (read-only)
    In production, this would connect to a real Analytics MCP server (Mixpanel, Amplitude, etc.)
    """
    scen = _scenario(account_id)
    if scen == "risk":
        active_users = 820
        active_users_change = -0.18
        engagement_score = 0.42
        feature_adoption = {"feature_a": 0.55, "feature_b": 0.28, "feature_c": 0.12}
        product_satisfaction = 3.6
    elif scen == "mixed":
        active_users = 1400
        active_users_change = 0.10
        engagement_score = 0.62
        feature_adoption = {"feature_a": 0.80, "feature_b": 0.40, "feature_c": 0.22}
        product_satisfaction = 4.0
    elif scen == "win":
        active_users = 2100
        active_users_change = 0.24
        engagement_score = 0.82
        feature_adoption = {"feature_a": 0.92, "feature_b": 0.78, "feature_c": 0.52}
        product_satisfaction = 4.6
    else:
        active_users = 1250
        active_users_change = 0.15
        engagement_score = 0.75
        feature_adoption = {"feature_a": 0.85, "feature_b": 0.60, "feature_c": 0.30}
        product_satisfaction = 4.2

    # Mock analytics data - replace with real MCP client call
    return {
        "account_id": account_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "active_users": active_users,
        "active_users_change": active_users_change,
        "feature_adoption": feature_adoption,
        "engagement_score": engagement_score,
        "login_frequency": 4.2,  # times per week
        "session_duration_avg": 45,  # minutes
        "product_satisfaction": product_satisfaction  # out of 5
    }

def fetch_support_data(account_id: str, period_start: date, period_end: date) -> Dict[str, Any]:
    """
    Fetch support and CSAT data from MCP server (read-only)
    In production, this would connect to a real Support MCP server (Zendesk, Intercom, etc.)
    """
    scen = _scenario(account_id)
    if scen == "risk":
        ticket_count = 32
        ticket_count_change = 0.35
        escalation_rate = 0.22
        csat_score = 3.7
        nps_score = 18
        support_trend = "worsening"
        recent_feedback = ["Response times slowed", "Recurring reliability incidents impacted the team"]
    elif scen == "mixed":
        ticket_count = 20
        ticket_count_change = 0.10
        escalation_rate = 0.18
        csat_score = 4.0
        nps_score = 40
        support_trend = "mixed"
        recent_feedback = ["Some escalations on performance", "Support helpful but needs faster turnaround"]
    elif scen == "win":
        ticket_count = 6
        ticket_count_change = -0.45
        escalation_rate = 0.03
        csat_score = 4.7
        nps_score = 72
        support_trend = "improving"
        recent_feedback = ["Excellent support responsiveness", "Smooth onboarding and enablement"]
    else:
        ticket_count = 12
        ticket_count_change = -0.20
        escalation_rate = 0.08
        csat_score = 4.5
        nps_score = 65
        support_trend = "improving"
        recent_feedback = ["Great support response time", "Knowledgeable support team"]

    # Mock support data - replace with real MCP client call
    return {
        "account_id": account_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "ticket_count": ticket_count,
        "ticket_count_change": ticket_count_change,
        "avg_resolution_time": 2.5,  # hours
        "escalation_rate": escalation_rate,
        "csat_score": csat_score,  # out of 5
        "nps_score": nps_score,
        "support_trend": support_trend,
        "recent_feedback": recent_feedback
    }
