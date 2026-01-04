# dashboard/app.py
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import json

st.set_page_config(page_title="Meeting Notes Analyzer", layout="wide")

API_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

def load_meetings():
    """Load meetings from API (placeholder - would need GET /meetings endpoint)"""
    # This would fetch from API in production
    return []

def main():
    st.title("📝 Meeting Notes Analyzer")
    st.markdown("Analyze meeting transcripts to extract action items, decisions, and insights")
    
    tab1, tab2, tab3 = st.tabs(["Analyze Meeting", "View Results", "Dashboard"])
    
    with tab1:
        st.header("Analyze a Meeting")
        
        meeting_id = st.text_input("Meeting ID", value=f"meeting-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        title = st.text_input("Meeting Title", placeholder="e.g., Q4 Planning Meeting")
        date = st.date_input("Meeting Date", value=datetime.now().date())
        time = st.time_input("Meeting Time", value=datetime.now().time())
        
        participants = st.text_area(
            "Participants (one per line)",
            placeholder="John Doe\nJane Smith\nMike Johnson"
        )
        participant_list = [p.strip() for p in participants.split("\n") if p.strip()]
        
        transcript = st.text_area(
            "Meeting Transcript",
            height=300,
            placeholder="Paste the meeting transcript here...\n\nJohn: We need to finalize the Q4 roadmap.\nJane: I will create a draft by Friday.\nJohn: Great, and we should review the budget."
        )
        
        if st.button("Analyze Meeting", type="primary"):
            if not transcript or len(transcript) < 10:
                st.error("Please provide a meeting transcript (at least 10 characters)")
                return
            
            # Prepare request
            meeting_datetime = datetime.combine(date, time)
            payload = {
                "meeting_id": meeting_id,
                "title": title or "Untitled Meeting",
                "date": meeting_datetime.isoformat(),
                "participants": participant_list,
                "transcript": transcript
            }
            
            # Call API
            try:
                with st.spinner("Analyzing meeting..."):
                    response = requests.post(f"{API_URL}/analyze", json=payload, timeout=60)
                    response.raise_for_status()
                    result = response.json()
                
                st.success("Meeting analyzed successfully!")
                st.session_state['last_analysis'] = result
                st.session_state['last_meeting_id'] = meeting_id
                
                # Display results
                st.subheader("Summary")
                st.write(result.get("summary", "No summary available"))
                
                # Action Items
                if result.get("action_items"):
                    st.subheader("Action Items")
                    for ai in result["action_items"]:
                        with st.expander(f"✅ {ai.get('description', 'N/A')}"):
                            st.write(f"**Assignee:** {ai.get('assignee', 'Unassigned')}")
                            st.write(f"**Due Date:** {ai.get('due_date', 'Not specified')}")
                            st.write(f"**Priority:** {ai.get('priority', 'medium').upper()}")
                            st.write(f"**Status:** {ai.get('status', 'open').upper()}")
                
                # Decisions
                if result.get("decisions"):
                    st.subheader("Decisions")
                    for dec in result["decisions"]:
                        st.write(f"• **{dec.get('decision_text', 'N/A')}**")
                        if dec.get("rationale"):
                            st.caption(f"Rationale: {dec.get('rationale')}")
                
                # Topics
                if result.get("topics"):
                    st.subheader("Key Topics")
                    for topic in result["topics"]:
                        st.write(f"• {topic.get('topic_text', 'N/A')}")
                
                # Follow-ups
                if result.get("follow_ups"):
                    st.subheader("Follow-up Items")
                    for fu in result["follow_ups"]:
                        st.write(f"• **{fu.get('item', 'N/A')}**")
                        st.caption(f"Suggested timeline: {fu.get('suggested_timeline', 'Not specified')}")
                
            except requests.exceptions.RequestException as e:
                st.error(f"Error calling API: {str(e)}")
                st.info("Make sure the API server is running at the specified URL")
    
    with tab2:
        st.header("View Meeting Results")
        
        if 'last_analysis' in st.session_state:
            result = st.session_state['last_analysis']
            meeting_id = st.session_state.get('last_meeting_id', 'Unknown')
            
            st.subheader(f"Meeting: {meeting_id}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Action Items", len(result.get("action_items", [])))
                st.metric("Decisions", len(result.get("decisions", [])))
            
            with col2:
                st.metric("Topics", len(result.get("topics", [])))
                st.metric("Follow-ups", len(result.get("follow_ups", [])))
            
            # Action Items Table
            if result.get("action_items"):
                st.subheader("Action Items")
                df_ai = pd.DataFrame(result["action_items"])
                st.dataframe(df_ai, use_container_width=True)
            
            # Decisions Table
            if result.get("decisions"):
                st.subheader("Decisions")
                df_dec = pd.DataFrame(result["decisions"])
                st.dataframe(df_dec, use_container_width=True)
        else:
            st.info("No meeting analysis available. Analyze a meeting in the 'Analyze Meeting' tab.")
    
    with tab3:
        st.header("Dashboard")
        st.info("Dashboard features coming soon! This will show analytics across multiple meetings.")

if __name__ == "__main__":
    main()

