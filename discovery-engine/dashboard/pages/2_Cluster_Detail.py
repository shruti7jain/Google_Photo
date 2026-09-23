import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Cluster Detail | Discovery Engine", page_icon="🔬", layout="wide")

st.title("🔬 Cluster Detail")

@st.cache_resource
def get_engine():
    return create_engine(os.getenv("DATABASE_URL"))

engine = get_engine()

# Fetch all clusters for the dropdown
clusters_df = pd.read_sql("SELECT cluster_id, label FROM clusters ORDER BY opportunity_score DESC", engine)

if clusters_df.empty:
    st.warning("No clusters found.")
    st.stop()

# Dropdown selection
cluster_options = clusters_df.apply(lambda row: f"[{row['cluster_id']}] {row['label']}", axis=1).tolist()
selected_str = st.selectbox("Select a Cluster to Analyze:", cluster_options)

# Parse selected cluster ID
selected_id = int(selected_str.split("]")[0].replace("[", ""))

# Fetch selected cluster data
cluster_data = pd.read_sql(f"SELECT * FROM clusters WHERE cluster_id = {selected_id}", engine).iloc[0]

# Display top section
st.header(cluster_data['label'])
st.markdown(f"**AI Summary:** {cluster_data['summary']}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Opportunity Score", f"{cluster_data['opportunity_score']:.1f}/100")
col2.metric("Total Documents", cluster_data['doc_count'])
col3.metric("Primary Failure Mode", cluster_data['primary_failure_mode'])
col4.metric("Primary Retrieval Type", cluster_data['primary_retrieval_type'])

st.divider()

# Layout for charts and evidence
left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("Source Breakdown")
    source_data = json.loads(cluster_data['source_breakdown'])
    if source_data:
        pie_df = pd.DataFrame(list(source_data.items()), columns=['Source', 'Count'])
        fig = px.pie(pie_df, values='Count', names='Source', hole=0.4, 
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No source data available.")
        
    st.subheader("Scoring Details")
    st.progress(cluster_data['volume_score'] / 100.0, text=f"Volume Score: {cluster_data['volume_score']:.1f}")
    st.progress(cluster_data['severity_score'] / 100.0, text=f"Severity Score: {cluster_data['severity_score']:.1f}")

with right_col:
    st.subheader("Top Verbatim Evidence")
    
    # Fetch evidence
    evidence_df = pd.read_sql(f"SELECT quote, source, rating, date FROM cluster_evidence WHERE cluster_id = {selected_id} LIMIT 5", engine)
    
    if not evidence_df.empty:
        for idx, row in evidence_df.iterrows():
            with st.chat_message("user"):
                st.write(f"\"{row['quote']}\"")
                meta = f"**Source:** {row['source']}"
                if pd.notna(row['rating']):
                    meta += f" | **Rating:** {'⭐' * int(row['rating'])}"
                if pd.notna(row['date']):
                    meta += f" | **Date:** {str(row['date'])[:10]}"
                st.caption(meta)
    else:
        st.write("No evidence quotes found for this cluster.")
