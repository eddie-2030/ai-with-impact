# dashboard/app.py
import os
import pandas as pd
import sqlalchemy as sa
import streamlit as st

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/cxqa")
engine = sa.create_engine(DATABASE_URL)

st.set_page_config(page_title="CX QA Dashboard", layout="wide")
st.title("CX QA – Scores & Insights")

@st.cache_data(ttl=60)
def load_data():
    with engine.connect() as con:
        query = """
        SELECT 
            c.conv_ext_id,
            c.started_at,
            c.channel,
            c.language,
            a.name as agent_name,
            s.overall_score,
            s.empathy_score,
            s.professionalism_score,
            s.solution_effectiveness_score,
            s.created_at as scored_at
        FROM conversations c
        JOIN agents a ON c.agent_id = a.id
        LEFT JOIN scores s ON c.id = s.conversation_id
        ORDER BY c.started_at DESC
        """
        return pd.read_sql(query, con)

# Load data
try:
    df = load_data()
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Conversations", len(df))
    
    with col2:
        avg_score = df['overall_score'].mean() if not df.empty else 0
        st.metric("Avg Overall Score", f"{avg_score:.2f}" if avg_score > 0 else "N/A")
    
    with col3:
        avg_empathy = df['empathy_score'].mean() if not df.empty else 0
        st.metric("Avg Empathy Score", f"{avg_empathy:.2f}" if avg_empathy > 0 else "N/A")
    
    with col4:
        scored_count = df['overall_score'].notna().sum()
        st.metric("Scored Conversations", scored_count)
    
    # Charts
    if not df.empty:
        st.subheader("Score Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if df['overall_score'].notna().any():
                st.bar_chart(df[['overall_score', 'empathy_score', 'professionalism_score', 'solution_effectiveness_score']].mean())
        
        with col2:
            channel_counts = df['channel'].value_counts()
            st.bar_chart(channel_counts)
    
    # Recent conversations table
    st.subheader("Recent Conversations")
    if not df.empty:
        # Format the data for display
        display_df = df.copy()
        display_df['started_at'] = pd.to_datetime(display_df['started_at']).dt.strftime('%Y-%m-%d %H:%M')
        display_df['scored_at'] = pd.to_datetime(display_df['scored_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Round scores to 2 decimal places
        score_columns = ['overall_score', 'empathy_score', 'professionalism_score', 'solution_effectiveness_score']
        for col in score_columns:
            if col in display_df.columns:
                display_df[col] = display_df[col].round(2)
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No conversations found. Add some conversation data to see the dashboard.")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Make sure the database is running and contains data.") 