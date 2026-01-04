# dashboard/app.py
import streamlit as st
import requests
from datetime import datetime
import time

st.set_page_config(page_title="Research Report Writer", layout="wide")

API_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

def main():
    st.title("📚 Research Report Writer")
    st.markdown("Multi-Agent AI System for Research & Analysis")
    
    tab1, tab2, tab3 = st.tabs(["Generate Report", "View Reports", "About"])
    
    with tab1:
        st.header("Generate Research Report")
        
        research_query = st.text_area(
            "Research Query",
            height=100,
            placeholder="Enter your research question or topic...\n\nExample: What is the impact of AI on healthcare costs?"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            max_sources = st.slider("Maximum Sources", min_value=5, max_value=50, value=20)
            research_type = st.selectbox("Research Type", ["comprehensive", "quick", "deep"])
        with col2:
            min_credibility = st.slider("Minimum Credibility Score", min_value=0.0, max_value=1.0, value=0.6, step=0.1)
        
        if st.button("Generate Research Report", type="primary"):
            if not research_query or len(research_query) < 10:
                st.error("Please enter a research query (at least 10 characters)")
                return
            
            # Prepare request
            payload = {
                "research_query": research_query,
                "research_type": research_type,
                "max_sources": max_sources,
                "min_credibility_score": min_credibility
            }
            
            # Call API
            try:
                with st.spinner("Researching... This may take a few minutes..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("Initializing research agents...")
                    progress_bar.progress(10)
                    
                    response = requests.post(f"{API_URL}/research", json=payload, timeout=300)
                    response.raise_for_status()
                    result = response.json()
                    
                    progress_bar.progress(100)
                    status_text.text("Research complete!")
                
                st.success("Research report generated successfully!")
                st.session_state['last_report'] = result
                st.session_state['last_request_id'] = result.get('request_id')
                
                # Display report
                if result.get('report'):
                    report = result['report']
                    
                    # Executive Summary
                    st.subheader("Executive Summary")
                    st.write(report.get('executive_summary', 'No summary available'))
                    
                    # Full Report
                    st.subheader("Research Report")
                    st.markdown(report.get('content', 'No report content available'))
                    
                    # References
                    st.subheader("References")
                    st.text(report.get('references', 'No references available'))
                    
                    # Metadata
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Word Count", report.get('word_count', 0))
                    with col2:
                        st.metric("Sources", report.get('source_count', 0))
                    with col3:
                        st.metric("Status", result.get('status', 'unknown'))
                
            except requests.exceptions.RequestException as e:
                st.error(f"Error calling API: {str(e)}")
                st.info("Make sure the API server is running at the specified URL")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with tab2:
        st.header("View Research Reports")
        
        request_id = st.text_input("Request ID", placeholder="Enter request ID to view report")
        
        if st.button("Load Report") or request_id:
            if request_id:
                try:
                    response = requests.get(f"{API_URL}/research/{request_id}", timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    
                    st.success("Report loaded successfully!")
                    
                    st.subheader(f"Research: {result.get('research_query', 'Unknown')}")
                    
                    if result.get('report'):
                        report = result['report']
                        
                        st.markdown("### Executive Summary")
                        st.write(report.get('executive_summary', 'No summary available'))
                        
                        st.markdown("### Full Report")
                        st.markdown(report.get('content', 'No report content available'))
                        
                        st.markdown("### References")
                        st.text(report.get('references', 'No references available'))
                        
                        st.divider()
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Word Count", report.get('word_count', 0))
                            st.metric("Sources", report.get('source_count', 0))
                        with col2:
                            st.metric("Status", result.get('status', 'unknown'))
                            st.metric("Created", result.get('created_at', 'Unknown')[:10] if result.get('created_at') else 'Unknown')
                except requests.exceptions.RequestException as e:
                    st.error(f"Error loading report: {str(e)}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.info("Enter a request ID to view a report")
        
        # Show last report if available
        if 'last_report' in st.session_state:
            st.divider()
            st.subheader("Last Generated Report")
            if st.button("View Last Report"):
                st.session_state['view_last'] = True
    
    with tab3:
        st.header("About Research Report Writer")
        st.markdown("""
        ### Multi-Agent Research System
        
        This system uses multiple specialized AI agents to conduct research:
        
        - **Research Agent**: Gathers information from web and academic sources
        - **Fact-Check Agent**: Verifies source credibility and validity
        - **Analysis Agent**: Analyzes findings and identifies patterns
        - **Synthesis Agent**: Combines findings into comprehensive reports
        
        ### Features
        
        - ✅ Source attribution and verification
        - ✅ APA 7th edition citations
        - ✅ Comprehensive research reports
        - ✅ Quality control with credibility scoring
        - ✅ Parallel agent processing
        
        ### How It Works
        
        1. Research Agent searches and gathers information from multiple sources
        2. Fact-Check Agent verifies source credibility
        3. Analysis Agent identifies patterns and insights
        4. Synthesis Agent generates the final report with proper citations
        """)

if __name__ == "__main__":
    main()

