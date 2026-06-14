"""
Risk Analytics Dashboard — Risk distributions, feature importance, anomaly visualization.
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


@st.cache_data
def load_data():
    try:
        citizens = pd.read_csv(PROCESSED_DIR / "master_citizens.csv")
        features = pd.read_csv(PROCESSED_DIR / "feature_vectors.csv") if (PROCESSED_DIR / "feature_vectors.csv").exists() else None
        importance = pd.read_csv(PROCESSED_DIR / "feature_importance.csv") if (PROCESSED_DIR / "feature_importance.csv").exists() else None
        return citizens, features, importance
    except FileNotFoundError:
        return None, None, None


def _layout(fig, h=400):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", height=h,
                      font=dict(family="Inter, sans-serif", color="#e8e8ed"),
                      margin=dict(l=40, r=20, t=40, b=40))
    return fig


st.markdown("## ⚠️ Risk Analytics")
st.markdown('<p style="color:#8888a0;">Anomaly detection results, risk scoring, and feature analysis</p>',
            unsafe_allow_html=True)

citizens, features, importance = load_data()
if citizens is None:
    st.warning("⚠️ No processed data found.")
    st.stop()

# ── Row 1: Risk Score Distribution ────────────────────────────────
if "deviation_score" in citizens.columns:
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        for cat, info in RISK_CATEGORIES.items():
            lo, hi = info["range"]
            mask = (citizens["deviation_score"] >= lo) & (citizens["deviation_score"] <= hi)
            subset = citizens[mask]
            if len(subset) > 0:
                fig.add_trace(go.Histogram(
                    x=subset["deviation_score"], name=f"Cat {cat}: {info['label']}",
                    marker_color=info["color"], opacity=0.8, nbinsx=10
                ))
        fig.update_layout(title="Risk Score Distribution by Category", barmode="stack",
                         xaxis_title="Deviation Score", yaxis_title="Count")
        fig = _layout(fig)
        st.plotly_chart(fig, use_container_width=True, theme=None)

    with col2:
        if "province" in citizens.columns:
            heatmap = pd.crosstab(citizens["province"], citizens["risk_category"])
            for cat in RISK_CATEGORIES:
                if cat not in heatmap.columns:
                    heatmap[cat] = 0
            heatmap = heatmap[sorted(heatmap.columns)]
            heatmap.columns = [f"Cat {c}" for c in heatmap.columns]
            fig = px.imshow(heatmap, title="Province × Risk Level Heatmap",
                           color_continuous_scale=["#0a0a0f", "#00d4aa", "#ffd000", "#ff3355"],
                           aspect="auto")
            fig = _layout(fig)
            st.plotly_chart(fig, use_container_width=True, theme=None)

# ── Row 2: Feature Importance ─────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if importance is not None and len(importance) > 0:
        top_features = importance.head(15)
        fig = px.bar(top_features, y="feature", x="importance",
                    title="Feature Importance (XGBoost)",
                    orientation="h", color="importance",
                    color_continuous_scale=["#4a9eff", "#00d4aa"])
        fig = _layout(fig, 450)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True, theme=None)
    else:
        st.info("Feature importance data not available — run ML pipeline to generate")

with col2:
    # Income vs Net Worth gap
    if "declared_income" in citizens.columns and "estimated_net_worth" in citizens.columns:
        gap_df = citizens[
            (citizens["estimated_net_worth"] > 0)
        ].head(1000).copy()
        gap_df["income_gap"] = gap_df["estimated_net_worth"] - gap_df["declared_income"]
        gap_df["gap_ratio"] = gap_df["declared_income"] / (gap_df["estimated_net_worth"] + 1)

        fig = px.scatter(gap_df, x="gap_ratio", y="deviation_score" if "deviation_score" in gap_df.columns else "income_gap",
                        color="risk_category" if "risk_category" in gap_df.columns else None,
                        color_discrete_map={k: v["color"] for k, v in RISK_CATEGORIES.items()},
                        title="Income-to-Wealth Gap Analysis",
                        labels={"gap_ratio": "Income / Net Worth Ratio",
                                "deviation_score": "Deviation Score"},
                        opacity=0.6)
        fig = _layout(fig, 450)
        st.plotly_chart(fig, use_container_width=True, theme=None)

# ── Row 3: Anomaly scatter (PCA) + Top patterns ──────────────────
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if features is not None and len(features) > 5:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler

        # Select numeric columns
        numeric_cols = features.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            X = features[numeric_cols].fillna(0).values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            pca = PCA(n_components=2)
            X_pca = pca.fit_transform(X_scaled)

            pca_df = pd.DataFrame({"PC1": X_pca[:, 0], "PC2": X_pca[:, 1]})
            if "risk_category" in citizens.columns and len(citizens) == len(pca_df):
                pca_df["Risk"] = citizens["risk_category"].values
            else:
                pca_df["Risk"] = "Unknown"

            fig = px.scatter(pca_df, x="PC1", y="PC2", color="Risk",
                           color_discrete_map={k: v["color"] for k, v in RISK_CATEGORIES.items()},
                           title=f"Anomaly Detection (PCA, {pca.explained_variance_ratio_.sum()*100:.1f}% var.)",
                           opacity=0.5)
            fig = _layout(fig, 400)
            st.plotly_chart(fig, use_container_width=True, theme=None)
    else:
        st.info("Feature vectors not available — run ML pipeline")

with col2:
    st.markdown("#### 🔍 Top Suspicious Patterns")
    if "deviation_score" in citizens.columns:
        suspicious = citizens.nlargest(20, "deviation_score")[
            ["canonical_name", "city", "declared_income", "estimated_net_worth",
             "deviation_score", "risk_category"]
        ].copy() if "estimated_net_worth" in citizens.columns else citizens.nlargest(20, "deviation_score")

        if "declared_income" in suspicious.columns:
            suspicious["declared_income"] = suspicious["declared_income"].apply(
                lambda x: f"PKR {x:,.0f}" if pd.notna(x) else "N/A")
        if "estimated_net_worth" in suspicious.columns:
            suspicious["estimated_net_worth"] = suspicious["estimated_net_worth"].apply(
                lambda x: f"PKR {x:,.0f}" if pd.notna(x) else "N/A")
        if "deviation_score" in suspicious.columns:
            suspicious["deviation_score"] = suspicious["deviation_score"].round(1)

        st.dataframe(suspicious, hide_index=True, use_container_width=True, height=400)
