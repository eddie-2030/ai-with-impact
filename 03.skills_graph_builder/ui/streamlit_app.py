import streamlit as st
import requests, pandas as pd, os

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Skills Graph Coach (LLM)", layout="wide")
st.title("🧭 Skills Graph Builder & Gap-to-Role Coach (LLM)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Health & Roles")
    if st.button("Check API Health"):
        st.success(requests.get(f"{API_URL}/health").json())
    roles = requests.get(f"{API_URL}/roles").json()
    flat_roles = [{"role_id": r["role_id"], "title": r["title"], "level": r["level"], "num_skills": len(r.get("skills",[]))} for r in roles]
    st.dataframe(pd.DataFrame(flat_roles))

with col2:
    st.subheader("People & Skills")
    persons = requests.get(f"{API_URL}/persons").json()
    pick = st.selectbox("Choose a person", persons, format_func=lambda x: f"{x.get('name','?')} ({x['person_id']})" if isinstance(x, dict) else str(x))
    if pick:
        pid = pick["person_id"]
        skills = requests.get(f"{API_URL}/person/{pid}/skills").json()
        st.dataframe(pd.DataFrame(skills))

st.markdown("---")

st.subheader("Matches & Plan")
if 'pid' not in locals() and persons:
    pid = persons[0]["person_id"]
left, right = st.columns(2)
with left:
    if persons:
        if st.button("Compute Role Matches"):
            matches = requests.get(f"{API_URL}/roles/matches", params={"person_id": pid, "top_k": 5}).json()
            st.dataframe(pd.DataFrame(matches))
with right:
    if persons:
        role_ids = [r["role_id"] for r in requests.get(f"{API_URL}/roles").json()]
        role_pick = st.selectbox("Target Role (optional)", ["<auto>"] + role_ids)
        if st.button("Generate Plan"):
            params = {} if role_pick=="<auto>" else {"role_id": role_pick}
            plan = requests.get(f"{API_URL}/recommendations/{pid}", params=params).json()
            st.json(plan)

st.caption("Tip: run scripts/generate_synth_data.py then scripts/load_seed_data.py before using the UI.")
