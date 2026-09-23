import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Leaderboard | Discovery Engine", page_icon="🏆", layout="wide")

st.title("🏆 Opportunity Leaderboard")
st.markdown("This table ranks all identified user pain points by their mathematically derived Opportunity Score (50% Volume + 50% Severity).")

@st.cache_data
def load_clusters():
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    query = """
    SELECT 
        cluster_id, label, primary_failure_mode, 
        doc_count, volume_score, severity_score, opportunity_score
    FROM clusters
    ORDER BY opportunity_score DESC
    """
    df = pd.read_sql(query, engine)
    
    df['opportunity_score'] = df['opportunity_score'].round(2)
    df['volume_score'] = df['volume_score'].round(2)
    df['severity_score'] = df['severity_score'].round(2)
    
    display_df = df.copy()
    display_df = display_df.rename(columns={
        "cluster_id": "ID",
        "label": "Cluster Label",
        "primary_failure_mode": "Primary Failure Mode",
        "doc_count": "Documents",
        "volume_score": "Volume Score (0-100)",
        "severity_score": "Severity Score (0-100)",
        "opportunity_score": "Opportunity Score (0-100)"
    })
    return display_df

with st.spinner("Loading clusters from database..."):
    df = load_clusters()
    
if not df.empty:
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Opportunity Score (0-100)": st.column_config.ProgressColumn(
                "Opportunity Score (0-100)",
                help="The final ranking score",
                format="%.1f",
                min_value=0,
                max_value=100,
            ),
        }
    )
    
    st.info("💡 Head over to the **Cluster Detail** page in the sidebar to drill down into a specific issue and read the verbatim evidence quotes.")
else:
    st.warning("No clusters found in the database. Did Phase 4 complete successfully?")
