# dashboard/app.py
import streamlit as st
import httpx
from datetime import date, datetime
from typing import Dict, Any, List
import json
import os
import time
from datetime import datetime as _dt

API_BASE_URL = st.secrets.get("API_BASE_URL", os.getenv("API_BASE_URL", "http://localhost:8000"))

st.set_page_config(
    page_title="Sales and Customer Success Quarterly Business Review Pack Builder",
    page_icon=None,
    layout="wide"
)

APP_TITLE = "Sales and Customer Success Quarterly Business Review Pack Builder"
st.title(APP_TITLE)
st.caption("Generate professional QBR packs from CRM, product analytics, and support signals with structured insights and an action plan.")

# Debug banner to confirm you're on the latest UI + which API it is calling
try:
    _mtime = os.path.getmtime(__file__)
    _build = _dt.fromtimestamp(_mtime).strftime("%Y-%m-%d %H:%M:%S")
except Exception:
    _build = "unknown"
st.caption(f"UI build: {_build} | API_BASE_URL: {API_BASE_URL}")

st.markdown(
    """
<style>
/* push content down so the H1 title isn't visually crowded/covered by Streamlit's top header */
div.block-container { padding-top: 3.0rem; }
/* extra breathing room for the main title */
h1 { margin-top: 0.75rem; }
div[data-testid="stMetricLabel"] p { font-weight: 600; }
.qbr-card {
  border: 1px solid rgba(49, 51, 63, 0.15);
  border-radius: 10px;
  padding: 14px 16px;
  background: rgba(49, 51, 63, 0.02);
}
</style>
""",
    unsafe_allow_html=True,
)

def _api_health() -> Dict[str, Any] | None:
    try:
        # NOTE: In some local Python environments, httpx may raise PermissionError while
        # creating an SSL context even for plain HTTP requests. `verify=False` avoids that.
        r = httpx.get(f"{API_BASE_URL}/health", timeout=2.0, verify=False)
        if r.status_code == 200:
            return r.json()
        return {"status": "unhealthy", "http_status": r.status_code}
    except Exception:
        return None

def _pill(label: str, tone: str = "neutral") -> str:
    colors = {
        "neutral": ("#111827", "rgba(17, 24, 39, 0.06)"),
        "good": ("#065f46", "rgba(6, 95, 70, 0.10)"),
        "warn": ("#92400e", "rgba(146, 64, 14, 0.10)"),
        "bad": ("#991b1b", "rgba(153, 27, 27, 0.10)"),
    }
    fg, bg = colors.get(tone, colors["neutral"])
    return f"<span style='color:{fg}; background:{bg}; padding:2px 10px; border-radius:999px; font-size:0.85rem; font-weight:600;'>{label}</span>"

def _format_number(value: Any, decimals: int = 0) -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
    except Exception:
        return str(value)
    if decimals == 0:
        return f"{num:,.0f}"
    return f"{num:,.{decimals}f}"

def _format_delta_percent(change_percent: Any, trend: str) -> str:
    if change_percent is None:
        return "—"
    try:
        num = float(change_percent)
    except Exception:
        return str(change_percent)
    trend_emoji = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend or "stable", "➡️")
    return f"{num:+.1f}% {trend_emoji}"

def _render_qbr_pack(pack_id: str, qbr: Dict[str, Any]) -> None:
    status = (qbr.get("status") or "unknown").lower()
    tone = "neutral"
    if status in ("pending_approval", "approved", "exported"):
        tone = "good"
    elif status in ("draft",):
        tone = "warn"
    elif status in ("failed", "rejected"):
        tone = "bad"

    st.markdown(
        f"<div class='qbr-card'><div style='display:flex; justify-content:space-between; align-items:center;'>"
        f"<div><div style='font-size:1.05rem; font-weight:700;'>QBR Pack</div>"
        f"<div style='color:rgba(17,24,39,0.7); font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace;'>{pack_id}</div>"
        f"</div><div>{_pill(status.replace('_',' ').title(), tone)}</div></div></div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", (qbr.get("status") or "unknown").replace("_", " ").title())
    with col2:
        st.metric("Version", qbr.get("version", 1))
    with col3:
        health_score = qbr.get("account_health_score", 0) or 0
        st.metric("Account Health Score", f"{float(health_score):.0%}")

    st.subheader("Executive Summary")
    st.write(qbr.get("executive_summary", "No summary available"))

    st.subheader("Insights")
    insights = qbr.get("insights", [])

    wins = [i for i in insights if i.get("type") == "win"]
    risks = [i for i in insights if i.get("type") == "risk"]
    opportunities = [i for i in insights if i.get("type") == "opportunity"]

    tab1, tab2, tab3 = st.tabs(["Wins", "Risks", "Opportunities"])

    with tab1:
        if not wins:
            st.caption("No wins identified.")
        for win in wins:
            with st.expander(f"{win.get('title', 'Win')}"):
                st.write(win.get("description", ""))
                st.caption(f"Impact: {win.get('impact_score', 0):.0%} | Confidence: {win.get('confidence_score', 0):.0%}")

    with tab2:
        if not risks:
            st.caption("No risks identified.")
        for risk in risks:
            with st.expander(f"{risk.get('title', 'Risk')}"):
                st.write(risk.get("description", ""))
                st.caption(f"Impact: {risk.get('impact_score', 0):.0%} | Confidence: {risk.get('confidence_score', 0):.0%}")

    with tab3:
        if not opportunities:
            st.caption("No opportunities identified.")
        for opp in opportunities:
            with st.expander(f"{opp.get('title', 'Opportunity')}"):
                st.write(opp.get("description", ""))
                st.caption(f"Impact: {opp.get('impact_score', 0):.0%} | Confidence: {opp.get('confidence_score', 0):.0%}")

    st.subheader("Action Plan")
    action_items = qbr.get("action_items", [])
    if not action_items:
        st.caption("No action items.")
    else:
        rows: List[Dict[str, Any]] = []
        for ai in action_items:
            rows.append(
                {
                    "Priority": (ai.get("priority") or "medium").title(),
                    "Action Item": ai.get("description", ""),
                    "Assignee": ai.get("assignee") or "Unassigned",
                    "Due": ai.get("due_date") or "—",
                    "Status": (ai.get("status") or "open").replace("_", " ").title(),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Key Metrics")
    metrics = qbr.get("metrics", [])
    if metrics:
        metric_cols = st.columns(min(len(metrics), 4))
        for idx, metric in enumerate(metrics[:4]):
            with metric_cols[idx % len(metric_cols)]:
                value = metric.get("value")
                unit = metric.get("unit", "") or ""
                change = metric.get("change_percent")
                trend = metric.get("trend", "stable")
                st.metric(
                    metric.get("name", "Metric"),
                    f"{_format_number(value, decimals=0)} {unit}".strip(),
                    _format_delta_percent(change, trend)
                )
    else:
        st.caption("No metrics available.")

def _poll_for_pack(pack_id: str, timeout_s: int = 90, interval_s: float = 2.0) -> Dict[str, Any] | None:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        r = httpx.get(f"{API_BASE_URL}/qbr/{pack_id}", timeout=10.0, verify=False)
        if r.status_code == 200:
            last = r.json()
            status = last.get("status")
            # Once the backend has populated insights + summary, it sets pending_approval
            if status in ("pending_approval", "approved", "exported", "rejected", "failed"):
                return last
        time.sleep(interval_s)
    return last

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Generate QBR", "View QBR", "Dashboard"])

with st.sidebar:
    st.markdown("---")
    st.subheader("System Status")
    health = _api_health()
    if health and health.get("status") == "healthy":
        st.markdown(_pill("API Healthy", "good"), unsafe_allow_html=True)
    elif health is None:
        st.markdown(_pill("API Unreachable", "bad"), unsafe_allow_html=True)
        st.caption("Start the API and ensure the UI points to the correct endpoint.")
    else:
        st.markdown(_pill("API Unhealthy", "warn"), unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("Test Account IDs")
    st.caption("Use these to drive different scenarios in the demo MCP data.")
    st.code("acc-win-001\nacc-risk-001\nacc-mixed-001", language="text")

if page == "Generate QBR":
    st.header("Generate a QBR Pack")
    st.caption("Provide the account and time period. The system will generate a draft pack for review.")
    
    with st.form("qbr_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            account_id = st.text_input("Account ID", value="acc-mixed-001", help="Try acc-win-001, acc-risk-001, or acc-mixed-001")
            account_name = st.text_input("Account Name", value="Acme Corp")
            quarter = st.selectbox("Quarter", ["Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025"])
        
        with col2:
            period_start = st.date_input("Period Start", value=date(2025, 1, 1))
            period_end = st.date_input("Period End", value=date(2025, 3, 31))
        
        goals = st.multiselect(
            "Goals/Focus Areas",
            ["Renewal", "Expansion", "Product Adoption", "Support Health", "Risk Mitigation"],
            default=["Renewal", "Expansion"]
        )
        
        submitted = st.form_submit_button("Generate QBR Pack")
        
        if submitted:
            if not account_id.strip():
                st.error("Account ID is required.")
                st.stop()
            if period_end < period_start:
                st.error("Period End must be on or after Period Start.")
                st.stop()

            with st.spinner("Starting QBR generation..."):
                try:
                    response = httpx.post(
                        f"{API_BASE_URL}/qbr/generate",
                        json={
                            "account_id": account_id,
                            "account_name": account_name,
                            "quarter": quarter,
                            "period_start": period_start.isoformat(),
                            "period_end": period_end.isoformat(),
                            "goals": goals
                        },
                        timeout=30.0,
                        verify=False,
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    pack_id = result["pack_id"]
                    st.session_state["last_pack_id"] = pack_id
                    st.success(f"QBR generation started. Pack ID: {pack_id}")

                    with st.spinner("Generating report (polling for completion)..."):
                        qbr = _poll_for_pack(pack_id, timeout_s=90, interval_s=2.0)

                    if not qbr:
                        st.warning("Still processing. Go to 'View QBR' and paste the Pack ID.")
                    else:
                        if qbr.get("status") == "failed":
                            st.error("Generation failed. Try again or check API logs.")
                        _render_qbr_pack(pack_id, qbr)
                    
                except Exception as e:
                    st.error(f"Error generating QBR: {str(e)}")

elif page == "View QBR":
    st.header("View QBR Pack")
    st.caption("Load an existing pack by Pack ID to review the full report.")
    
    default_pack_id = st.session_state.get("last_pack_id", "")
    pack_id = st.text_input("Enter Pack ID", value=default_pack_id)
    
    if pack_id:
        with st.spinner("Loading QBR pack..."):
            try:
                response = httpx.get(f"{API_BASE_URL}/qbr/{pack_id}", timeout=10.0, verify=False)
                response.raise_for_status()
                qbr = response.json()

                _render_qbr_pack(pack_id, qbr)
                
                # Approval Section
                st.subheader("Approval")
                if qbr.get("status") == "pending_approval":
                    with st.form("approval_form"):
                        action = st.radio("Action", ["approve", "request_changes", "reject"])
                        approver_name = st.text_input("Your Name")
                        feedback = st.text_area("Feedback (optional)")
                        
                        if st.form_submit_button("Submit"):
                            try:
                                response = httpx.post(
                                    f"{API_BASE_URL}/qbr/{pack_id}/approve",
                                    json={
                                        "action": action,
                                        "approver_name": approver_name,
                                        "feedback": feedback
                                    },
                                    timeout=10.0,
                                    verify=False,
                                )
                                response.raise_for_status()
                                st.success(f"QBR pack {action}d successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                else:
                    st.info(f"Status: {qbr.get('status', 'unknown')}")
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    st.error("QBR pack not found")
                else:
                    st.error(f"Error loading QBR: {str(e)}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

elif page == "Dashboard":
    st.header("Portfolio Dashboard")
    st.info("Portfolio analytics view is a planned enhancement.")
    st.markdown(
        """
Planned additions:
- QBR generation volume and freshness
- Account health trends over time
- Insight distribution by category
- Action item completion rate and aging
"""
    )
