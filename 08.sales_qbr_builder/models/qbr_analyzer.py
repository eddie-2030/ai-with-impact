# models/qbr_analyzer.py
from __future__ import annotations
import os
import json
from typing import Dict, List, Any, Optional
from datetime import date, timedelta
from pydantic import BaseModel, Field, ValidationError
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

_client = None


class InsightModel(BaseModel):
    type: str = Field(..., pattern="^(win|risk|opportunity)$")
    title: str
    description: str = ""
    impact_score: float = Field(0.5, ge=0.0, le=1.0)
    confidence_score: float = Field(0.5, ge=0.0, le=1.0)
    category: str = "general"


class ActionItemModel(BaseModel):
    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None  # ISO date YYYY-MM-DD
    priority: str = Field("medium", pattern="^(low|medium|high)$")


class MetricModel(BaseModel):
    name: str
    value: float | int | None = None
    unit: str = ""
    comparison_value: float | int | None = None
    change_percent: float | int | None = None
    trend: str = Field("stable", pattern="^(up|down|stable)$")


class QBRResultModel(BaseModel):
    executive_summary: str = ""
    account_health_score: float = Field(0.5, ge=0.0, le=1.0)
    insights: List[InsightModel] = Field(default_factory=list)
    action_items: List[ActionItemModel] = Field(default_factory=list)
    metrics: List[MetricModel] = Field(default_factory=list)

def _get_openai_client():
    """
    Lazily initialize the OpenAI client.
    This avoids import-time failures when SSL/certs or env are not configured yet,
    and lets the API boot even if OpenAI isn't available.
    """
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def _heuristic_qbr_report(
    account_name: str,
    aggregated_data: Dict[str, Any],
    goals: List[str],
    period_start: date,
    period_end: date,
) -> Dict[str, Any]:
    """
    Deterministic fallback report generator.
    Produces a complete QBR report even if OpenAI is unavailable/errors.
    """
    crm = aggregated_data.get("crm", {}) or {}
    analytics = aggregated_data.get("analytics", {}) or {}
    support = aggregated_data.get("support", {}) or {}

    def _due(days_after_end: int) -> str:
        return (period_end + timedelta(days=days_after_end)).isoformat()

    renewal_prob = float(crm.get("renewal_probability") or 0.5)
    engagement = float(analytics.get("engagement_score") or 0.5)
    csat = float(support.get("csat_score") or 4.0)  # 1-5 scale
    escalation = float(support.get("escalation_rate") or 0.0)
    au_change = float(analytics.get("active_users_change") or 0.0)
    tickets_change = float(support.get("ticket_count_change") or 0.0)
    feature_adoption = analytics.get("feature_adoption") or {}
    active_users = float(analytics.get("active_users") or 0)
    ticket_count = float(support.get("ticket_count") or 0)

    csat_norm = max(0.0, min(1.0, csat / 5.0))
    escalation_norm = 1.0 - max(0.0, min(1.0, escalation / 0.25))  # 25% escalation is bad
    change_norm = max(0.0, min(1.0, 0.5 + au_change))  # -0.5..+0.5 mapped

    health = (renewal_prob + engagement + csat_norm + escalation_norm + change_norm) / 5.0
    health = max(0.0, min(1.0, health))

    wins: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    opps: List[Dict[str, Any]] = []

    if au_change > 0.05:
        wins.append({
            "type": "win",
            "title": "Usage is growing",
            "description": f"Active users increased by ~{au_change:.0%} over the period.",
            "impact_score": 0.7,
            "confidence_score": 0.7,
            "category": "usage",
        })
    if tickets_change < -0.10:
        wins.append({
            "type": "win",
            "title": "Support load improving",
            "description": f"Ticket volume decreased by ~{abs(tickets_change):.0%}.",
            "impact_score": 0.6,
            "confidence_score": 0.6,
            "category": "support",
        })
    if csat >= 4.3:
        wins.append({
            "type": "win",
            "title": "Strong customer satisfaction",
            "description": f"CSAT is {csat:.1f}/5, indicating strong satisfaction.",
            "impact_score": 0.7,
            "confidence_score": 0.7,
            "category": "support",
        })

    if renewal_prob < 0.70:
        risks.append({
            "type": "risk",
            "title": "Renewal risk",
            "description": f"Renewal probability is {renewal_prob:.0%}. Prioritize executive alignment and value proof.",
            "impact_score": 0.8,
            "confidence_score": 0.6,
            "category": "contract",
        })
    if escalation > 0.15:
        risks.append({
            "type": "risk",
            "title": "Escalation risk",
            "description": f"Escalation rate is {escalation:.0%}. Investigate root causes and set proactive outreach.",
            "impact_score": 0.8,
            "confidence_score": 0.6,
            "category": "support",
        })

    low_features = [
        k for k, v in feature_adoption.items()
        if isinstance(v, (int, float)) and v < 0.35
    ]
    if low_features:
        opps.append({
            "type": "opportunity",
            "title": "Increase feature adoption",
            "description": f"Low adoption observed for: {', '.join(low_features)}. Target enablement and a success plan to drive adoption.",
            "impact_score": 0.7,
            "confidence_score": 0.6,
            "category": "product",
        })

    crm_opps = crm.get("opportunities") or []
    if crm_opps:
        top = crm_opps[0] or {}
        opps.append({
            "type": "opportunity",
            "title": "Expansion opportunity",
            "description": f"Pipeline includes '{top.get('name')}' valued at ~{top.get('value', 0):,}. Align roadmap/value and close plan.",
            "impact_score": 0.8,
            "confidence_score": 0.6,
            "category": "contract",
        })

    insights = [*wins, *risks, *opps]
    goals_str = ", ".join(goals) if goals else "General account health"

    action_items = [
        {
            "description": "Confirm renewal path and stakeholders; schedule exec sync and circulate a renewal plan",
            "assignee": "Customer Success Manager",
            "due_date": _due(7),
            "priority": "high" if renewal_prob < 0.75 else "medium",
        },
        {
            "description": "Draft adoption plan for underutilized features (enablement + success milestones)",
            "assignee": "Solutions Engineer",
            "due_date": _due(14),
            "priority": "medium",
        },
        {
            "description": "Review top support themes and create proactive remediation plan",
            "assignee": "Support Lead",
            "due_date": _due(10),
            "priority": "medium",
        },
    ]

    metrics = [
        {
            "name": "Renewal Probability",
            "value": renewal_prob * 100,
            "unit": "%",
            "comparison_value": None,
            "change_percent": None,
            "trend": "stable",
        },
        {
            "name": "Active Users",
            "value": float(analytics.get("active_users") or 0),
            "unit": "",
            "comparison_value": None,
            "change_percent": au_change * 100,
            "trend": "up" if au_change > 0 else "down" if au_change < 0 else "stable",
        },
        {
            "name": "CSAT",
            "value": csat,
            "unit": "/5",
            "comparison_value": None,
            "change_percent": None,
            "trend": "stable",
        },
        {
            "name": "Tickets",
            "value": float(support.get("ticket_count") or 0),
            "unit": "",
            "comparison_value": None,
            "change_percent": tickets_change * 100,
            "trend": "down" if tickets_change < 0 else "up" if tickets_change > 0 else "stable",
        },
    ]

    def _top_titles(items: List[Dict[str, Any]], n: int = 2) -> str:
        titles = [i.get("title") for i in items if i.get("title")]
        return ", ".join(titles[:n]) if titles else "no major themes"

    wins_txt = _top_titles(wins, 2)
    risks_txt = _top_titles(risks, 2)
    opps_txt = _top_titles(opps, 2)

    executive_summary = (
        f"Over {period_start.isoformat()} to {period_end.isoformat()}, {account_name} shows an overall account health score of "
        f"{health:.0%} against goals ({goals_str}). Leading indicators include {active_users:,.0f} active users "
        f"({au_change:+.0%} vs prior), CSAT {csat:.1f}/5, and {ticket_count:,.0f} support tickets "
        f"({tickets_change:+.0%}). Key wins: {wins_txt}. Primary risks to address: {risks_txt}. "
        f"Top opportunities: {opps_txt}. Recommended next steps are captured as action items with owners and near-term due dates "
        f"to drive execution before the next stakeholder review."
    )

    return {
        "executive_summary": executive_summary,
        "account_health_score": health,
        "insights": insights,
        "action_items": action_items,
        "metrics": metrics,
    }

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

    # If no API key is configured, still return a complete report.
    if not os.getenv("OPENAI_API_KEY"):
        return _heuristic_qbr_report(account_name, aggregated_data, goals, period_start, period_end)
    
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
        # Only initialize OpenAI client when needed
        client = _get_openai_client()
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
        raw = json.loads(response_text)

        # Validate shape via Pydantic (reliability layer / structured outputs)
        try:
            parsed = QBRResultModel.model_validate(raw)
            result = parsed.model_dump()
        except ValidationError as ve:
            # If the LLM returns invalid structure/types, fall back to heuristic
            out = _heuristic_qbr_report(account_name, aggregated_data, goals, period_start, period_end)
            out["error"] = f"Structured output validation failed: {ve.errors()[:3]}"
            return out
        
        # Ensure all required fields exist (defensive; should already be validated)
        result.setdefault("executive_summary", "")
        result.setdefault("account_health_score", 0.5)
        result.setdefault("insights", [])
        result.setdefault("action_items", [])
        result.setdefault("metrics", [])

        # Enrich/normalize action items so UI & DB always have assignee/due_date.
        def _due(days_after_end: int) -> str:
            return (period_end + timedelta(days=days_after_end)).isoformat()

        default_assignees = {
            "renewal": "Customer Success Manager",
            "expansion": "Account Executive",
            "adoption": "Solutions Engineer",
            "support": "Support Lead",
            "product": "Product Manager",
        }

        for idx, ai in enumerate(result.get("action_items", []) or []):
            if not isinstance(ai, dict):
                continue

            desc = (ai.get("description") or "").lower()
            if not ai.get("assignee"):
                if "renew" in desc or "stakeholder" in desc:
                    ai["assignee"] = default_assignees["renewal"]
                elif "expand" in desc or "upsell" in desc or "cross-sell" in desc:
                    ai["assignee"] = default_assignees["expansion"]
                elif "adopt" in desc or "enable" in desc or "training" in desc:
                    ai["assignee"] = default_assignees["adoption"]
                elif "support" in desc or "ticket" in desc or "escalat" in desc:
                    ai["assignee"] = default_assignees["support"]
                else:
                    ai["assignee"] = default_assignees["renewal"]

            if not ai.get("due_date"):
                pr = (ai.get("priority") or "medium").lower()
                if pr == "high":
                    ai["due_date"] = _due(7)
                elif pr == "low":
                    ai["due_date"] = _due(21)
                else:
                    ai["due_date"] = _due(14)

        # If the executive summary is too thin, replace it with an insight-grounded paragraph.
        summary = (result.get("executive_summary") or "").strip()
        if len(summary) < 160:
            wins = [i for i in (result.get("insights") or []) if i.get("type") == "win"]
            risks = [i for i in (result.get("insights") or []) if i.get("type") == "risk"]
            opps = [i for i in (result.get("insights") or []) if i.get("type") == "opportunity"]

            def _top_titles(items: List[Dict[str, Any]], n: int = 2) -> str:
                titles = [i.get("title") for i in items if i.get("title")]
                return ", ".join(titles[:n]) if titles else "no major themes"

            wins_txt = _top_titles(wins, 2)
            risks_txt = _top_titles(risks, 2)
            opps_txt = _top_titles(opps, 2)
            goals_str = ", ".join(goals) if goals else "General account health"
            health = float(result.get("account_health_score") or 0.5)
            result["executive_summary"] = (
                f"Over {period_start.isoformat()} to {period_end.isoformat()}, {account_name} is tracking at an overall health score "
                f"of {health:.0%} against goals ({goals_str}). Key wins include {wins_txt}. Risks to mitigate next include {risks_txt}. "
                f"Opportunities to pursue include {opps_txt}. Action items below assign clear owners and due dates to drive progress "
                f"before the next QBR review."
            )
        
        # Validate insight types
        for insight in result.get("insights", []):
            if insight.get("type") not in ["win", "risk", "opportunity"]:
                insight["type"] = "opportunity"  # Default
        
        return result
    
    except Exception as e:
        # Fallback response: still produce a complete report, attach error for debugging
        out = _heuristic_qbr_report(account_name, aggregated_data, goals, period_start, period_end)
        out["error"] = str(e)
        return out
