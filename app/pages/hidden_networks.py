"""
Hidden Networks — Graph AI analysis to find groups of people hiding wealth.
"""
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.data_service import DataService
from core.network_analysis.network_detector import NetworkDetector

st.set_page_config(page_title="Hidden Networks", page_icon="🕸️", layout="wide")

st.markdown("## 🕸️ Hidden Wealth Networks")
st.markdown(
    '<p style="color:#8888a0;">Detecting families and syndicates hiding assets using Graph Traversal</p>',
    unsafe_allow_html=True
)

@st.cache_data(ttl=60)
def load_network_data():
    svc = DataService()
    svc.reload()
    if not svc.is_loaded:
        return None, None
    
    detector = NetworkDetector(svc.graph, svc.citizens_df)
    networks = detector.find_suspicious_networks()
    shell_companies = detector.detect_shell_companies()
    return networks, shell_companies

networks, shell_companies = load_network_data()

if networks is None:
    st.warning("⚠️ No data loaded. Please run the pipeline first.")
    st.stop()

# ── Summary Metrics ────────────────────────────────────────────────
total_networks = len(networks)
total_hidden = sum(n["hidden_wealth"] for n in networks)

col1, col2, col3 = st.columns(3)
col1.metric("Suspicious Networks Detected", f"{total_networks:,}")
col2.metric("Total Hidden Wealth in Networks", f"{total_hidden / 1e9:.2f} Billion PKR")
col3.metric("Shell Companies Flagged", f"{len(shell_companies):,}")
st.markdown("---")

# ── Networks List ──────────────────────────────────────────────────
st.markdown("### 🚨 Top Flagged Networks")

def format_pkr(val):
    if val > 1e9: return f"{val/1e9:.1f}B"
    if val > 1e6: return f"{val/1e6:.1f}M"
    return f"{val:,.0f}"

for idx, net in enumerate(networks[:10]):  # Show top 10
    with st.expander(f"🔴 Network #{idx+1} — {len(net['members'])} Members — Hidden: {format_pkr(net['hidden_wealth'])} PKR"):
        str_members = [str(m) for m in net['members'][:10]]
        st.markdown(f"**Members:** {', '.join(str_members)}{'...' if len(net['members'])>10 else ''}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Combined Declared Income", f"{format_pkr(net['combined_income'])}")
        c2.metric("Combined Estimated Wealth", f"{format_pkr(net['combined_wealth'])}")
        c3.metric("Companies Involved", net["companies_involved"])
        
        # We could draw a pyvis graph here for this specific component!
        st.markdown("*Graph AI identified these individuals as highly connected through shared properties, businesses, or phones.*")

# ── Shell Companies ────────────────────────────────────────────────
st.markdown("### 🏢 Potential Shell Companies")
if shell_companies:
    df_shells = pd.DataFrame(shell_companies)
    st.dataframe(df_shells, use_container_width=True, hide_index=True)
else:
    st.info("No obvious shell companies detected in the current data slice.")
