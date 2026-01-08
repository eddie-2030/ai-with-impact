# dashboard/app.py
import streamlit as st
import requests
import os
from pathlib import Path

st.set_page_config(page_title="Code Security Reviewer", layout="wide")

API_URL = st.sidebar.text_input("API URL", value="http://localhost:8000")

# Get test cases directory
TEST_CASES_DIR = Path(__file__).parent.parent / "data" / "test_cases"

def load_test_case(file_path: Path) -> str:
    """Load test case file"""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error loading file: {str(e)}"

def get_test_cases() -> dict:
    """Get all available test cases"""
    test_cases = {}
    
    # Python test cases
    python_dir = TEST_CASES_DIR / "python"
    if python_dir.exists():
        for category in ["secure", "insecure", "efficient", "inefficient"]:
            category_dir = python_dir / category
            if category_dir.exists():
                for file in category_dir.glob("*.py"):
                    key = f"Python - {category.title()} - {file.stem}"
                    test_cases[key] = {
                        "path": file,
                        "language": "python",
                        "category": category
                    }
    
    # SQL test cases
    sql_dir = TEST_CASES_DIR / "sql"
    if sql_dir.exists():
        for category in ["secure", "insecure", "efficient", "inefficient"]:
            category_dir = sql_dir / category
            if category_dir.exists():
                for file in category_dir.glob("*.sql"):
                    key = f"SQL - {category.title()} - {file.stem}"
                    test_cases[key] = {
                        "path": file,
                        "language": "sql",
                        "category": category
                    }
    
    return test_cases

def main():
    st.title("🔒 Code Security Reviewer")
    st.markdown("Multi-Agent AI System for Code Review, Security Analysis & Auto-Rewrite")
    
    tab1, tab2, tab3 = st.tabs(["Test Cases", "Custom Code", "Review History"])
    
    with tab1:
        st.header("Test with Example Code")
        st.markdown("Select from pre-configured test cases to see the agents in action!")
        
        test_cases = get_test_cases()
        
        if not test_cases:
            st.warning("No test cases found. Please ensure test cases are in data/test_cases/")
        else:
            # Test case selector
            selected_test = st.selectbox(
                "Select Test Case",
                options=list(test_cases.keys()),
                help="Choose a test case to review"
            )
            
            if selected_test:
                test_info = test_cases[selected_test]
                code = load_test_case(test_info["path"])
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("Code to Review")
                    st.code(code, language=test_info["language"])
                
                with col2:
                    st.subheader("Test Case Info")
                    st.write(f"**Language:** {test_info['language'].upper()}")
                    st.write(f"**Category:** {test_info['category'].title()}")
                    st.write(f"**File:** {test_info['path'].name}")
                
                if st.button("🔍 Review Code", type="primary", use_container_width=True):
                    with st.spinner("Analyzing code with multi-agent system..."):
                        try:
                            response = requests.post(
                                f"{API_URL}/review",
                                json={
                                    "code": code,
                                    "language": test_info["language"],
                                    "file_path": str(test_info["path"])
                                },
                                timeout=60
                            )
                            response.raise_for_status()
                            result = response.json()
                            
                            st.session_state['last_review'] = result
                            display_review_results(result, test_info["language"])
                            
                        except requests.exceptions.RequestException as e:
                            st.error(f"Error calling API: {str(e)}")
                            st.info("Make sure the API server is running at the specified URL")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.header("Review Custom Code")
        
        language = st.selectbox("Language", ["python", "sql", "javascript", "java"])
        
        code_input = st.text_area(
            "Enter Code to Review",
            height=300,
            placeholder="Paste your code here..."
        )
        
        if st.button("🔍 Review Code", type="primary"):
            if not code_input.strip():
                st.warning("Please enter code to review")
            else:
                with st.spinner("Analyzing code with multi-agent system..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/review",
                            json={
                                "code": code_input,
                                "language": language
                            },
                            timeout=60
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        st.session_state['last_review'] = result
                        display_review_results(result, language)
                        
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error calling API: {str(e)}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab3:
        st.header("Review History")
        st.info("Review history feature coming soon!")

def display_review_results(result: dict, language: str):
    """Display comprehensive review results"""
    st.success("Code review completed!")
    
    summary = result.get("summary", {})
    
    # Overall scores
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Security Score", f"{summary.get('security_score', 0):.1f}/100")
    with col2:
        st.metric("Performance Score", f"{summary.get('performance_score', 0):.1f}/100")
    with col3:
        st.metric("Quality Score", f"{summary.get('quality_score', 0):.1f}/100")
    with col4:
        overall = summary.get("overall_score", 0)
        color = "🟢" if overall >= 80 else "🟡" if overall >= 60 else "🔴"
        st.metric("Overall Score", f"{color} {overall:.1f}/100")
    
    # Findings summary
    st.subheader("📊 Findings Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Critical", summary.get("critical_findings", 0))
    with col2:
        st.metric("High", summary.get("high_findings", 0))
    with col3:
        st.metric("Medium", summary.get("medium_findings", 0))
    with col4:
        st.metric("Low", summary.get("low_findings", 0))
    
    # Security Findings
    security = result.get("security", {})
    if security.get("findings"):
        with st.expander(f"🔒 Security Findings ({len(security['findings'])})", expanded=True):
            for finding in security["findings"]:
                severity_color = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }
                severity = finding.get("severity", "medium")
                st.markdown(f"**{severity_color.get(severity, '⚪')} {finding.get('finding_type', 'Unknown')}** ({severity.upper()})")
                st.write(f"*{finding.get('description', 'No description')}*")
                if finding.get("code_snippet"):
                    st.code(finding["code_snippet"], language=language)
                st.divider()
    
    # Performance Findings
    performance = result.get("performance", {})
    if performance.get("findings"):
        with st.expander(f"⚡ Performance Findings ({len(performance['findings'])})"):
            for finding in performance["findings"]:
                severity = finding.get("severity", "medium")
                st.markdown(f"**{finding.get('finding_type', 'Unknown')}** ({severity.upper()})")
                st.write(f"*{finding.get('description', 'No description')}*")
                if finding.get("code_snippet"):
                    st.code(finding["code_snippet"], language=language)
                if finding.get("current_complexity"):
                    st.write(f"Complexity: {finding.get('current_complexity')} → {finding.get('suggested_complexity', 'N/A')}")
                st.divider()
    
    # Quality Findings
    quality = result.get("quality", {})
    if quality.get("findings"):
        with st.expander(f"✨ Quality Findings ({len(quality['findings'])})"):
            for finding in quality["findings"]:
                severity = finding.get("severity", "medium")
                st.markdown(f"**{finding.get('finding_type', 'Unknown')}** ({severity.upper()})")
                st.write(f"*{finding.get('description', 'No description')}*")
                if finding.get("code_snippet"):
                    st.code(finding["code_snippet"], language=language)
                st.divider()
    
    # Code Rewrites
    rewrites = result.get("rewrites", [])
    if rewrites:
        st.subheader("🔧 Code Rewrites")
        st.markdown("Automatically generated code fixes:")
        
        for i, rewrite in enumerate(rewrites, 1):
            with st.expander(f"Rewrite #{i}: {rewrite.get('finding_type', 'Unknown')} (Confidence: {rewrite.get('confidence_score', 0):.1f}%)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Original Code:**")
                    st.code(rewrite.get("original_code", ""), language=language)
                
                with col2:
                    rewrite_mode = rewrite.get("rewrite_mode", "suggest")
                    mode_color = {
                        "auto_apply": "🟢 Auto-Apply",
                        "suggest": "🟡 Suggest",
                        "review": "🔴 Review"
                    }
                    st.markdown(f"**Rewritten Code:** {mode_color.get(rewrite_mode, rewrite_mode)}")
                    st.code(rewrite.get("rewritten_code", ""), language=language)
                
                if rewrite.get("explanation"):
                    st.info(f"**Explanation:** {rewrite['explanation']}")
    
    # Summary
    if summary.get("summary"):
        st.subheader("📝 Review Summary")
        st.write(summary["summary"])
    
    if summary.get("recommendations"):
        st.subheader("💡 Recommendations")
        st.write(summary["recommendations"])

if __name__ == "__main__":
    main()

