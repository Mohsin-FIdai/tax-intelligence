"""
Executive Dashboard — C-suite overview of the tax intelligence platform.
"""
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import PROCESSED_DIR, RISK_CATEGORIES, THEME


@st.cache_data(ttl=60)
def load_data():
    try:
        citizens = pd.read_csv(PROCESSED_DIR / "master_citizens.csv", low_memory=False)
        return citizens
    except FileNotFoundError:
        return None


def _plotly_layout(fig, height=400):
    """Apply consistent dark theme to plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#e8e8ed"),
        height=height,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def metric_card(label, value, delta=None, icon="📊", color="#00d4aa"):
    delta_html = ""
    if delta is not None:
        d_color = "#00d4aa" if delta >= 0 else "#ff3355"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<div style="color:{d_color}; font-size:0.8rem;">{arrow} {abs(delta):.1f}%</div>'

    st.markdown(f"""
    <div class="metric-card" style="border-top: 3px solid {color};">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.5rem;">{icon}</span>
        </div>
        <div style="font-size:0.75rem; color:#8888a0; margin-top:0.5rem; text-transform:uppercase;
                    letter-spacing:1px;">{label}</div>
        <div style="font-size:1.8rem; font-weight:700; color:#e8e8ed; margin:0.2rem 0;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ─── Page content ──────────────────────────────────────────────────
st.markdown("## 📊 National Tax Recovery Dashboard")
st.markdown('<p style="color:#8888a0;">Real-time overview of national tax compliance intelligence and estimated recoverable revenue</p>',
            unsafe_allow_html=True)

citizens = load_data()
if citizens is None:
    st.warning("⚠️ No processed data found. Please run the data pipeline first: "
               "`python run_pipeline.py`")
    st.stop()

# ── Compute metrics ────────────────────────────────────────────────
total = len(citizens)
filers = len(citizens[citizens["filing_status"].astype(str).str.lower().isin(["filed", "late filer", "filer"])]) if "filing_status" in citizens.columns else 0
non_filers = total - filers

# Risk categories
if "risk_category" in citizens.columns:
    suspicious = len(citizens[citizens["risk_category"].isin(["C", "D", "E"])])
    high_risk = len(citizens[citizens["risk_category"].isin(["D", "E"])])
else:
    suspicious = 0
    high_risk = 0

avg_score = citizens["deviation_score"].mean() if "deviation_score" in citizens.columns else 0

# Calculate financial metrics
total_hidden_income = citizens["estimated_hidden_income"].sum() if "estimated_hidden_income" in citizens.columns else 0
total_recoverable_tax = citizens["estimated_recoverable_tax"].sum() if "estimated_recoverable_tax" in citizens.columns else 0

def format_pkr(value):
    if pd.isna(value):
        return "0"
    if value >= 1e12:
        return f"{value / 1e12:.2f}T PKR"
    elif value >= 1e9:
        return f"{value / 1e9:.1f}B PKR"
    elif value >= 1e6:
        return f"{value / 1e6:.1f}M PKR"
    else:
        return f"{value:,.0f} PKR"

# ── KPI Cards ──────────────────────────────────────────────────────
cols = st.columns(4)
with cols[0]:
    metric_card("Total Citizens", f"{total:,}", icon="👥", color="#4a9eff")
with cols[1]:
    metric_card("High Risk (Cat D+E)", f"{high_risk:,}", icon="🔴", color="#ff3355")
with cols[2]:
    metric_card("Potential Hidden Income", f"{format_pkr(total_hidden_income)}", icon="💰", color="#ffd000")
with cols[3]:
    metric_card("Est. Recoverable Tax", f"{format_pkr(total_recoverable_tax)}", icon="🏛️", color="#00d4aa")

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Risk Distribution + Filing Status ──────────────────────
col1, col2 = st.columns(2)

with col1:
    if "risk_category" in citizens.columns:
        risk_dist = citizens["risk_category"].value_counts().reset_index()
        risk_dist.columns = ["Category", "Count"]
        risk_dist["Label"] = risk_dist["Category"].map(
            {k: f"Cat {k}: {v['label']}" for k, v in RISK_CATEGORIES.items()}
        )
        risk_dist["Color"] = risk_dist["Category"].map(
            {k: v["color"] for k, v in RISK_CATEGORIES.items()}
        )
        fig = px.pie(risk_dist, values="Count", names="Label",
                     title="Risk Category Distribution",
                     color="Label",
                     color_discrete_map={row["Label"]: row["Color"] for _, row in risk_dist.iterrows()},
                     hole=0.5)
        fig = _plotly_layout(fig, 380)
        st.plotly_chart(fig, use_container_width=True, theme=None)
    else:
        st.info("Risk categories not computed yet")

with col2:
    if "filing_status" in citizens.columns:
        filing_dist = citizens["filing_status"].value_counts().reset_index()
        filing_dist.columns = ["Status", "Count"]
        # Ensure status matches map exactly
        filing_dist["Status"] = filing_dist["Status"].astype(str).str.title()
        color_map = {"Filer": "#00d4aa", "Filed": "#00d4aa", "Non-Filer": "#ff3355", "Late Filer": "#ffd000"}
        fig = px.bar(filing_dist, x="Status", y="Count", title="Filing Status Breakdown",
                     color="Status", color_discrete_map=color_map)
        fig = _plotly_layout(fig, 380)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True, theme=None)
    else:
        st.info("Filing status data not available")

# ── Row 2: Province Heatmap + Top 10 ─────────────────────────────
col1, col2 = st.columns(2)

with col1:

    if "province" in citizens.columns and "estimated_recoverable_tax" in citizens.columns:
        gap_data = citizens.groupby("province")["estimated_recoverable_tax"].sum().reset_index()
        gap_data = gap_data.sort_values("estimated_recoverable_tax", ascending=False)
        
        fig = px.bar(gap_data, x="province", y="estimated_recoverable_tax", 
                     title="Estimated Recoverable Tax by Province (PKR)",
                     color="estimated_recoverable_tax",
                     color_continuous_scale="Viridis")
        fig = _plotly_layout(fig, 380)
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True, theme=None)

with col2:
    if "estimated_recoverable_tax" in citizens.columns:
        req_cols = ["canonical_name", "cnic", "city", "estimated_recoverable_tax", "risk_category"]
        avail_cols = [c for c in req_cols if c in citizens.columns]
        all_risk = citizens.sort_values("estimated_recoverable_tax", ascending=False)[avail_cols].copy()
        
        # Rename columns that exist
        rename_map = {"canonical_name": "Name", "cnic": "CNIC", "city": "City", 
                      "estimated_recoverable_tax": "Tax Gap", "risk_category": "Risk"}
        all_risk.rename(columns={k: v for k, v in rename_map.items() if k in avail_cols}, inplace=True)
        
        st.markdown("#### 🔴 Highest Risk Citizens (By Tax Gap)")
        
        if "Risk" in all_risk.columns:
            categories = ["All"] + sorted(all_risk["Risk"].dropna().unique().tolist())
            selected_cat = st.selectbox("Filter by Risk Category", categories, index=0)
            
            if selected_cat != "All":
                display_df = all_risk[all_risk["Risk"] == selected_cat]
            else:
                display_df = all_risk
        else:
            display_df = all_risk
            
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

# ── Row 3: Income vs Net Worth Scatter ────────────────────────────
if "declared_income" in citizens.columns and "estimated_net_worth" in citizens.columns:
    st.markdown("---")
    scatter_df = citizens[
        (citizens["declared_income"] > 0) & (citizens["estimated_net_worth"] > 0)
    ].head(2000).copy()

    if len(scatter_df) > 0:
        fig = px.scatter(
            scatter_df,
            x="declared_income", y="estimated_net_worth",
            color="risk_category" if "risk_category" in scatter_df.columns else None,
            color_discrete_map={k: v["color"] for k, v in RISK_CATEGORIES.items()},
            title="Declared Income vs. Estimated Net Worth",
            labels={"declared_income": "Declared Income (PKR)", "estimated_net_worth": "Est. Net Worth (PKR)"},
            hover_data=["canonical_name", "cnic"] if "canonical_name" in scatter_df.columns else None,
            opacity=0.7,
        )
        # Add reference line (y = x) for perfect compliance
        max_val = max(scatter_df["declared_income"].max(), scatter_df["estimated_net_worth"].max())
        fig.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val],
                                 mode="lines", name="Perfect Compliance",
                                 line=dict(dash="dash", color="#8888a0", width=1)))
        fig = _plotly_layout(fig, 450)
        st.plotly_chart(fig, use_container_width=True, theme=None)

