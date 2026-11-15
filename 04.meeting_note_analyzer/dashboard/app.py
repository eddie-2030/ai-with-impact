# dashboard/app.py
import streamlit as st
import requests
from datetime import datetime
from uuid import uuid4

st.set_page_config(page_title="Meeting Notes Analyzer", layout="wide")

API_URL = st.sidebar.text_input("API URL", value="http://127.0.0.1:8000").rstrip("/")

def main():
    st.title("📝 Meeting Notes Analyzer")
    st.markdown("Analyze meeting transcripts to extract action items, decisions, and insights")
    
    tab1, tab2, tab3 = st.tabs(["Analyze Meeting", "View Results", "Dashboard"])
    
    with tab1:
        st.header("Analyze a Meeting")
        
        if "default_meeting_id" not in st.session_state:
            st.session_state["default_meeting_id"] = f"meeting-{uuid4().hex}"
            st.session_state["default_meeting_time"] = datetime.now()
        meeting_id = st.text_input("Meeting ID", value=st.session_state["default_meeting_id"])
        title = st.text_input("Meeting Title", placeholder="e.g., Q4 Planning Meeting")
        default_time = st.session_state["default_meeting_time"]
        date = st.date_input("Meeting Date", value=default_time.date())
        time = st.time_input("Meeting Time", value=default_time.time())
        
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
                st.text(result.get("summary") or "No summary available")
                
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
                        st.text(dec.get("decision_text") or "")
                        if dec.get("rationale"):
                            st.text(dec["rationale"])
                
                # Topics
                if result.get("topics"):
                    st.subheader("Key Topics")
                    for topic in result["topics"]:
                        st.text(topic.get("topic_text") or "")
                
                # Follow-ups
                if result.get("follow_ups"):
                    st.subheader("Follow-up Items")
                    for fu in result["follow_ups"]:
                        st.text(fu.get("item") or "")
                        st.text(f"Suggested timeline: {fu.get('suggested_timeline') or 'Not specified'}")
                
            except requests.exceptions.HTTPError as error:
                messages = {
                    409: "This meeting ID is already in use. Reuse the original input or enter a new ID.",
                    422: "Check the meeting ID, date, and transcript.",
                    502: "The model returned an unusable analysis.",
                    503: "The model is unavailable. Check the API configuration and try again.",
                }
                st.error(messages.get(error.response.status_code, "The API could not analyze the meeting."))
            except requests.exceptions.RequestException:
                st.error("Could not reach the API. Check the server and API URL.")
    
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
                st.dataframe(result["action_items"], width="stretch")
            
            # Decisions Table
            if result.get("decisions"):
                st.subheader("Decisions")
                st.dataframe(result["decisions"], width="stretch")
        else:
            st.info("No meeting analysis available. Analyze a meeting in the 'Analyze Meeting' tab.")
    
    with tab3:
        st.header("Dashboard")
        st.info("Dashboard features coming soon! This will show analytics across multiple meetings.")

if __name__ == "__main__":
    main()


