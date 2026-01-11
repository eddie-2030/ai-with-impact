# models/qbr_analyzer.py
from __future__ import annotations
import os
import json
from typing import Dict, List, Any, Optional
from datetime import date
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

PROMPT_TEMPLATE = """Analyze the following aggregated data for a Quarterly Business Review (QBR) and generate structured insights.

Account: {account_name}
Period: {period_start} to {period_end}
Goals: {goals}

CRM Data:
{crm_data}

Analytics Data:
{analytics_data}

Support Data:
{support_data}

Please analyze this data and return a JSON object with the following structure:
{{
  "executive_summary": "A concise 2-3 sentence summary of the account's performance and health",
  "account_health_score": 0.0-1.0,
  "insights": [
    {{
      "type": "win, risk, or opportunity",
      "title": "Short title for the insight",
      "description": "Detailed description of the insight",
      "impact_score": 0.0-1.0,
      "confidence_score": 0.0-1.0,
      "category": "usage, support, contract, product, etc."
    }}
  ],
  "action_items": [
    {{
      "description": "Recommended action item",
      "assignee": "Suggested assignee (or null)",
      "due_date": "YYYY-MM-DD or null",
      "priority": "low, medium, or high"
    }}
  ],
  "metrics": [
    {{
      "name": "Metric name",
      "value": numeric_value,
      "unit": "unit of measurement",
      "comparison_value": previous_period_value,
      "change_percent": percentage_change,
      "trend": "up, down, or stable"
    }}
  ]
}}

Focus on identifying:
- Wins: Positive trends, achievements, successful implementations
- Risks: Usage declines, support escalations, contract risks, health deterioration
- Opportunities: Expansion opportunities, upsell potential, feature gaps, growth areas

Return ONLY valid JSON, no additional text."""

def aggregate_qbr_data(
    crm_data: Dict[str, Any],
    analytics_data: Dict[str, Any],
    support_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Aggregate and validate data from multiple sources"""
    
    aggregated = {
        "crm": crm_data,
        "analytics": analytics_data,
        "support": support_data
    }
    
    # Perform basic sanity checks
    if crm_data.get("arr") and analytics_data.get("mrr"):
        # Check for consistency (ARR should be ~12x MRR)
        arr = crm_data.get("arr", 0)
        mrr = analytics_data.get("mrr", 0)
        if mrr > 0:
            ratio = arr / (mrr * 12)
            if ratio < 0.8 or ratio > 1.2:
                aggregated["data_quality_warnings"] = [
                    f"ARR/MRR ratio ({ratio:.2f}) is outside expected range (0.8-1.2)"
                ]
    
    return aggregated

def generate_qbr_insights(
    account_name: str,
    aggregated_data: Dict[str, Any],
    goals: List[str],
    period_start: date,
    period_end: date
) -> Dict[str, Any]:
    """Generate QBR insights using LLM"""
    
    goals_str = ", ".join(goals) if goals else "General account health"
    
    # Format data for prompt
    crm_data_str = json.dumps(aggregated_data.get("crm", {}), indent=2)
    analytics_data_str = json.dumps(aggregated_data.get("analytics", {}), indent=2)
    support_data_str = json.dumps(aggregated_data.get("support", {}), indent=2)
    
    prompt = PROMPT_TEMPLATE.format(
        account_name=account_name,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        goals=goals_str,
        crm_data=crm_data_str,
        analytics_data=analytics_data_str,
        support_data=support_data_str
    )
    
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a QBR analysis assistant. You analyze account data and generate structured insights. Always return valid JSON only."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        response_text = completion.choices[0].message.content
        result = json.loads(response_text)
        
        # Ensure all required fields exist
        result.setdefault("executive_summary", "")
        result.setdefault("account_health_score", 0.5)
        result.setdefault("insights", [])
        result.setdefault("action_items", [])
        result.setdefault("metrics", [])
        
        # Validate insight types
        for insight in result.get("insights", []):
            if insight.get("type") not in ["win", "risk", "opportunity"]:
                insight["type"] = "opportunity"  # Default
        
        return result
    
    except Exception as e:
        # Fallback response
        return {
            "executive_summary": f"QBR analysis for {account_name} for period {period_start} to {period_end}.",
            "account_health_score": 0.5,
            "insights": [],
            "action_items": [],
            "metrics": [],
            "error": str(e)
        }
