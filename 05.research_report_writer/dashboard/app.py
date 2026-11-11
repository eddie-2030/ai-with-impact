import os
from urllib.parse import quote

import requests
import streamlit as st


API_URL = os.getenv("RESEARCH_API_URL", "http://127.0.0.1:8000").rstrip("/")


def call_api(method: str, path: str, *, payload: dict | None = None):
    try:
        response = requests.request(method, f"{API_URL}{path}", json=payload, timeout=120)
    except requests.RequestException:
        st.error("The report API did not respond. Check the API address and try again.")
        return None

    try:
        data = response.json()
    except ValueError:
        st.error(f"The report API returned an unreadable response (HTTP {response.status_code}).")
        return None

    if not response.ok:
        detail = data.get("detail") if isinstance(data, dict) else None
        message = detail.get("message") if isinstance(detail, dict) else detail
        st.error(message if isinstance(message, str) else f"Research failed (HTTP {response.status_code}).")
        return None
    if not isinstance(data, dict):
        st.error("The report API did not return a report record.")
        return None
    return data


def display_report(result: dict):
    report = result.get("report")
    if result.get("status") != "completed" or not report:
        st.error("This request has no completed report.")
        return

    mode = result.get("search_mode")
    if mode == "fixture":
        st.info("Fixture mode. This offline example uses synthetic evidence.")
    elif mode == "tavily":
        st.caption("Source excerpts from Tavily. Review the sources before relying on the report.")
    else:
        st.info("This saved report predates recorded search provenance.")

    st.text(f"Request ID: {result['request_id']}")
    st.markdown(report["content"])
    st.subheader("References")
    st.text(report["references"])
    columns = st.columns(2)
    columns[0].metric("Word count", report["word_count"])
    columns[1].metric("Sources", report["source_count"])


def main():
    st.set_page_config(page_title="Research Report Writer", layout="wide")
    st.title("Research Report Writer")
    generate, saved = st.tabs(["Generate report", "Find saved report"])

    with generate:
        query = st.text_area("Research question", height=100)
        left, right = st.columns(2)
        with left:
            max_sources = st.slider("Maximum sources", min_value=1, max_value=20, value=20)
        with right:
            min_credibility = st.slider("Minimum source score (heuristic)", 0.0, 1.0, 0.5, 0.05)

        if st.button("Generate research report", type="primary"):
            if len(query.strip()) < 10:
                st.error("Enter a research question with at least 10 characters.")
            else:
                with st.spinner("Gathering evidence and preparing a report"):
                    result = call_api("POST", "/research", payload={
                        "research_query": query.strip(),
                        "max_sources": max_sources,
                        "min_credibility_score": min_credibility,
                    })
                if result:
                    display_report(result)

    with saved:
        request_id = st.text_input("Request ID")
        if st.button("Load report"):
            if not request_id.strip():
                st.info("Enter a request ID from a generated report.")
            else:
                result = call_api("GET", f"/research/{quote(request_id.strip(), safe='')}")
                if result:
                    display_report(result)


if __name__ == "__main__":
    main()
