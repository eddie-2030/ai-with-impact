import streamlit as st
import requests, pandas as pd, os

API_URL = os.environ.get("API_URL", "http://localhost:8000")


def api_get(path, params=None):
    try:
        response = requests.get(f"{API_URL}{path}", params=params, timeout=30)
    except requests.RequestException:
        st.error("The Skills Graph API did not respond. Check that it is running and try again.")
        return None

    try:
        payload = response.json()
    except ValueError:
        st.error(f"The API returned an unreadable response (HTTP {response.status_code}).")
        return None

    if not response.ok:
        detail = payload.get("detail") if isinstance(payload, dict) else None
        message = detail.get("message") if isinstance(detail, dict) else detail
        st.error(message if isinstance(message, str) else f"The request failed (HTTP {response.status_code}).")
        return None
    return payload


st.set_page_config(page_title="Skills Graph Coach (LLM)", layout="wide")
st.title("🧭 Skills Graph Builder & Gap-to-Role Coach (LLM)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Health & Roles")
    if st.button("Check API Health"):
        health = api_get("/health")
        if health is not None:
            st.success("The API is running.")
    roles = api_get("/roles") or []
    flat_roles = [{"role_id": r["role_id"], "title": r["title"], "level": r["level"], "num_skills": len(r.get("skills",[]))} for r in roles]
    st.dataframe(pd.DataFrame(flat_roles))

with col2:
    st.subheader("People & Skills")
    persons = api_get("/persons") or []
    pick = st.selectbox("Choose a person", persons, format_func=lambda x: f"{x.get('name','?')} ({x['person_id']})" if isinstance(x, dict) else str(x))
    if pick:
        pid = pick["person_id"]
        skills = api_get(f"/person/{pid}/skills")
        if skills:
            st.dataframe(pd.DataFrame(skills))
        elif skills == []:
            st.info("This profile has no extracted skills. Ingest evidence to generate role matches.")

st.markdown("---")

st.subheader("Matches & Plan")
if 'pid' not in locals() and persons:
    pid = persons[0]["person_id"]
left, right = st.columns(2)
with left:
    if persons:
        if st.button("Compute Role Matches"):
            matches = api_get("/roles/matches", params={"person_id": pid, "top_k": 5})
            if matches:
                st.dataframe(pd.DataFrame(matches))
            elif matches == []:
                st.info("No roles to rank. Ingest skill evidence first.")
with right:
    if persons:
        role_ids = [r["role_id"] for r in roles]
        role_pick = st.selectbox("Target Role (optional)", ["<auto>"] + role_ids)
        if st.button("Generate Plan"):
            params = {} if role_pick=="<auto>" else {"role_id": role_pick}
            plan = api_get(f"/recommendations/{pid}", params=params)
            if plan is not None:
                st.json(plan)

st.caption("To try role matching, configure the model provider and ingest a synthetic profile. See the README.")
