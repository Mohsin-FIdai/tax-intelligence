"""
Tax Intelligence Platform — Main Streamlit Application
"""
import sys
from pathlib import Path

import streamlit as st

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ─── Page config (MUST be first Streamlit command) ──────────────────
st.set_page_config(
    page_title="Tax Intelligence Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Load custom CSS ───────────────────────────────────────────────
css_path = Path(__file__).parent / "styles" / "theme.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# ─── Page definitions ──────────────────────────────────────────────
pages_dir = Path(__file__).parent / "pages"

executive = st.Page(str(pages_dir / "executive_dashboard.py"),
                    title="Executive Dashboard", icon="📊")
data_upload = st.Page(str(pages_dir / "data_upload.py"),
                      title="Data Ingestion Hub", icon="📥", default=True)
entity_res = st.Page(str(pages_dir / "entity_resolution.py"),
                     title="Entity Resolution", icon="🔗")
knowledge_graph = st.Page(str(pages_dir / "knowledge_graph.py"),
                          title="Knowledge Graph", icon="🕸️")
risk_analytics = st.Page(str(pages_dir / "risk_analytics.py"),
                         title="Risk Analytics", icon="⚠️")
citizen_profile = st.Page(str(pages_dir / "citizen_profile.py"),
                          title="Citizen Profile", icon="👤")
hidden_networks = st.Page(str(pages_dir / "hidden_networks.py"),
                          title="Hidden Networks", icon="🕸️")
geo_heatmap = st.Page(str(pages_dir / "geo_heatmap.py"),
                      title="Geographic Heat Maps", icon="🗺️")
investigation = st.Page(str(pages_dir / "investigation_center.py"),
                        title="Investigation Center", icon="🔎")

data_scenarios = st.Page(str(pages_dir / "data_scenarios.py"),
                         title="Data Scenarios Hub", icon="🧪")

pg = st.navigation({
    "System": [data_upload, data_scenarios],
    "Overview": [executive, geo_heatmap],
    "Analysis": [entity_res, knowledge_graph, hidden_networks, risk_analytics],
    "Investigation": [citizen_profile, investigation],
})

# ─── Sidebar branding ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
        <div style="font-size: 2.2rem;">🔍</div>
        <h2 style="margin:0; color:#00d4aa; font-size:1.1rem; letter-spacing:1px;">
            TAX INTELLIGENCE
        </h2>
        <p style="margin:0; color:#8888a0; font-size:0.7rem; letter-spacing:2px;">
            BY TECH TITANS
        </p>
        <hr style="border-color:#2a2a3e; margin: 0.8rem 0;">
    </div>
    """, unsafe_allow_html=True)

pg.run()
