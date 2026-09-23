import streamlit as st

st.set_page_config(
    page_title="Discovery Engine | Google Photos",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Google Photos Discovery Engine 🔍")
st.markdown("""
Welcome to the Discovery Engine PM Dashboard! 

Use the sidebar to navigate:
- **🏆 Opportunity Leaderboard**: View the top mathematically ranked pain points and feature requests.
- **🔬 Cluster Detail**: Dive deep into a specific pain point to see the verbatim user feedback and metadata breakdown.
""")

st.info("👈 Select a page from the sidebar to begin.")
