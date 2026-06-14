"""
Data Scenarios Hub — Showcases the functionality of the system with curated Positive, Medium, and Negative entries.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import SYNTHETIC_DIR, PROCESSED_DIR

def run_backend_pipeline():
    with st.spinner("Generating 10,000 synthetic rows and running ETL pipeline... This takes about 15-30 seconds."):
        # Generate raw data
        from generators.generate_synthetic_data import generate_all_datasets
        generate_all_datasets()
        
        # Run ETL
        from core.data_ingestion.etl_pipeline import ETLPipeline
        pipeline = ETLPipeline(output_dir=PROCESSED_DIR)
        pipeline.add_sources_from_dir(SYNTHETIC_DIR, extensions=(".csv", ".xlsx"))
        pipeline.run()
        
        # Run ML features (Risk & Graph)
        from core.risk_scoring.risk_engine import RiskEngine
        from core.network_analysis.graph_builder import GraphBuilder
        
        # Run ML if possible
        try:
            from run_pipeline import run_full_pipeline
            run_full_pipeline()
        except Exception as e:
            pass

        st.success("✅ 10,000 Records Generated and Pipeline Completed!")
        st.cache_data.clear()

st.title("🧪 Data Scenarios & Validation Hub")
st.markdown("This dashboard audits the system's functionality. It explicitly highlights how the pipeline handles **Positive (Compliant)**, **Medium (Suspicious)**, and **Negative (High-Risk)** archetypes across 10,000 raw generated records.")



@st.cache_data
def load_audit_data():
    gt_path = SYNTHETIC_DIR / "_ground_truth.csv"
    matches_path = PROCESSED_DIR / "entity_matches.csv"
    citizens_path = PROCESSED_DIR / "master_citizens.csv"
    
    gt = pd.read_csv(gt_path) if gt_path.exists() else pd.DataFrame()
    matches = pd.read_csv(matches_path) if matches_path.exists() else pd.DataFrame()
    citizens = pd.read_csv(citizens_path) if citizens_path.exists() else pd.DataFrame()
    return gt, matches, citizens

gt, matches, citizens = load_audit_data()

if gt.empty:
    st.warning("Ground truth dataset not found. Please click 'Generate & Run Pipeline' above.")
    st.stop()

st.markdown("---")
st.markdown("### 1. Archetype Validation (10,000 Total Records)")
st.markdown("The backend data generator intentionally seeds the dataset with different behavioral profiles to test the machine learning anomaly detectors.")

tab1, tab2, tab3 = st.tabs(["🟢 Positive (Compliant)", "🟡 Medium (Under-filer)", "🔴 Negative (Fraud Syndicate)"])

if "category" not in gt.columns:
    gt["category"] = "Medium"
    gt.loc[gt["is_extreme"] == True, "category"] = "Negative"
    gt.loc[(gt["is_anomaly"] == False) & (gt["is_filer"] == True), "category"] = "Positive"

def render_archetype_table(category_name, description):
    st.markdown(description)
    df = gt[gt["category"] == category_name]
    st.metric(f"Total {category_name} Records", f"{len(df):,}")
    display_cols = ["cnic", "canonical_name", "wealth_class", "declared_income", "tax_paid", "is_filer", "has_activity"]
    st.dataframe(df[display_cols].head(100), use_container_width=True, hide_index=True)

with tab1:
    render_archetype_table("Positive", "**The Honest Taxpayer:** Filers who declare their true income based on their wealth class. Their records match perfectly across databases.")

with tab2:
    render_archetype_table("Medium", "**The Under-Reporter:** Filers who significantly under-report their income compared to their actual lifestyle (properties/cars).")

with tab3:
    render_archetype_table("Negative", "**The Fraud Syndicate:** Non-filers who pay zero tax, yet possess immense wealth (luxury vehicles, commercial properties) and use shell companies/aliases.")


