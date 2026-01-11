# dashboard/app.py
import streamlit as st
import httpx
from datetime import date, datetime
from typing import Dict, Any
import json

API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Sales/CS QBR Pack Builder",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Sales/CS QBR Pack Builder")
st.markdown("Generate comprehensive Quarterly Business Review packs with AI-powered insights")

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Generate QBR", "View QBR", "Dashboard"])

if page == "Generate QBR":
    st.header("Generate New QBR Pack")
    
    with st.form("qbr_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            account_id = st.text_input("Account ID", value="acc-001")
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
            with st.spinner("Generating QBR pack..."):
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
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    st.success(f"QBR generation started! Pack ID: {result['pack_id']}")
                    st.info(f"Status: {result['status']}. Use 'View QBR' to check progress.")
                    
                except Exception as e:
                    st.error(f"Error generating QBR: {str(e)}")

elif page == "View QBR":
    st.header("View QBR Pack")
    
    pack_id = st.text_input("Enter Pack ID", value="")
    
    if pack_id:
        with st.spinner("Loading QBR pack..."):
            try:
                response = httpx.get(f"{API_BASE_URL}/qbr/{pack_id}", timeout=10.0)
                response.raise_for_status()
                qbr = response.json()
                
                # Display QBR pack
                st.subheader(f"QBR Pack: {pack_id}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Status", qbr.get("status", "unknown"))
                with col2:
                    st.metric("Version", qbr.get("version", 1))
                with col3:
                    health_score = qbr.get("account_health_score", 0)
                    st.metric("Account Health", f"{health_score:.0%}")
                
                # Executive Summary
                st.subheader("Executive Summary")
                st.write(qbr.get("executive_summary", "No summary available"))
                
                # Insights
                st.subheader("Insights")
                insights = qbr.get("insights", [])
                
                wins = [i for i in insights if i.get("type") == "win"]
                risks = [i for i in insights if i.get("type") == "risk"]
                opportunities = [i for i in insights if i.get("type") == "opportunity"]
                
                tab1, tab2, tab3 = st.tabs(["Wins", "Risks", "Opportunities"])
                
                with tab1:
                    for win in wins:
                        with st.expander(f"✅ {win.get('title', 'Win')}"):
                            st.write(win.get("description", ""))
                            st.caption(f"Impact: {win.get('impact_score', 0):.0%} | Confidence: {win.get('confidence_score', 0):.0%}")
                
                with tab2:
                    for risk in risks:
                        with st.expander(f"⚠️ {risk.get('title', 'Risk')}"):
                            st.write(risk.get("description", ""))
                            st.caption(f"Impact: {risk.get('impact_score', 0):.0%} | Confidence: {risk.get('confidence_score', 0):.0%}")
                
                with tab3:
                    for opp in opportunities:
                        with st.expander(f"💡 {opp.get('title', 'Opportunity')}"):
                            st.write(opp.get("description", ""))
                            st.caption(f"Impact: {opp.get('impact_score', 0):.0%} | Confidence: {opp.get('confidence_score', 0):.0%}")
                
                # Action Items
                st.subheader("Action Items")
                action_items = qbr.get("action_items", [])
                for ai in action_items:
                    priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(ai.get("priority", "medium"), "⚪")
                    st.write(f"{priority_color} **{ai.get('description', '')}**")
                    st.caption(f"Assignee: {ai.get('assignee', 'Unassigned')} | Due: {ai.get('due_date', 'Not set')} | Status: {ai.get('status', 'open')}")
                
                # Metrics
                st.subheader("Key Metrics")
                metrics = qbr.get("metrics", [])
                if metrics:
                    metric_cols = st.columns(min(len(metrics), 4))
                    for idx, metric in enumerate(metrics[:4]):
                        with metric_cols[idx % len(metric_cols)]:
                            value = metric.get("value", 0)
                            change = metric.get("change_percent", 0)
                            trend = metric.get("trend", "stable")
                            trend_emoji = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend, "➡️")
                            st.metric(
                                metric.get("name", "Metric"),
                                f"{value:,.0f} {metric.get('unit', '')}",
                                f"{change:+.1f}% {trend_emoji}"
                            )
                
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
                                    timeout=10.0
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
    st.header("QBR Dashboard")
    st.info("Dashboard analytics coming soon!")
    st.markdown("""
    Future features:
    - QBR generation statistics
    - Account health trends
    - Insight category distribution
    - Action item completion rates
    """)
