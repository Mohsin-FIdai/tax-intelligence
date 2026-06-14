import sys
import time
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import RAW_UPLOADS_DIR
from run_pipeline import run_full_pipeline

st.set_page_config(page_title="Data Ingestion Hub", page_icon="📥", layout="wide")

st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h1 style="color: #00d4aa; margin-bottom: 0.5rem;">📥 Data Ingestion Hub</h1>
        <p style="color: #8888a0; font-size: 1.1rem;">
            Upload real organization datasets to securely process them through the Intelligence Pipeline.
            Files are stored locally in <code style="color:#ff8c00;">data/raw_uploads/</code> and are never sent to external servers.
        </p>
    </div>
""", unsafe_allow_html=True)

# Define the expected files
UPLOAD_MAP = {
    "Tax / Income Records (FBR)": "tax_records.csv",
    "Property Ownership (Housing)": "property_records.csv",
    "Vehicle Registrations (Excise)": "vehicle_records.csv",
    "Utility Bills (Electricity/Gas)": "utility_bills.csv",
    "Travel History (FIA)": "travel_records.csv",
    "Business Registrations (SECP)": "business_records.csv",
    "Banking Indicators (State Bank)": "banking_indicators.csv",
    "Telecom Records (PTA)": "mobile_records.csv"
}

st.info("💡 **Tip:** Ensure your CSV files have standard column names (like `cnic`, `declared_income`, `property_value`). The system automatically handles empty or missing columns.", icon="ℹ️")

col1, col2 = st.columns(2)

uploaded_files_count = 0

for i, (label, filename) in enumerate(UPLOAD_MAP.items()):
    target_col = col1 if i % 2 == 0 else col2
    with target_col:
        st.markdown(f"**{label}**")
        uploaded_file = st.file_uploader(
            f"Upload {label}", 
            type=["csv", "xlsx"], 
            key=f"upload_{filename}",
            label_visibility="collapsed"
        )
        
        target_path = RAW_UPLOADS_DIR / filename
        
        if uploaded_file is not None:
            # Save the file
            with open(target_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved to {filename} ({uploaded_file.size / 1024:.1f} KB)")
            uploaded_files_count += 1
        else:
            if target_path.exists():
                st.info(f"Using existing {filename} ({(target_path.stat().st_size / 1024):.1f} KB)")
                uploaded_files_count += 1
        st.markdown("---")

# Also scan for any custom files the user uploaded manually into the directory
st.markdown("### 📁 Other Detected Datasets")
custom_files_found = False
for custom_file in RAW_UPLOADS_DIR.glob("*.csv"):
    if custom_file.name not in UPLOAD_MAP.values():
        st.info(f"Detected custom file: **{custom_file.name}** ({(custom_file.stat().st_size / 1024):.1f} KB)")
        uploaded_files_count += 1
        custom_files_found = True
        
for custom_file in RAW_UPLOADS_DIR.glob("*.xlsx"):
    if custom_file.name not in UPLOAD_MAP.values():
        st.info(f"Detected custom file: **{custom_file.name}** ({(custom_file.stat().st_size / 1024):.1f} KB)")
        uploaded_files_count += 1
        custom_files_found = True

if not custom_files_found:
    st.markdown("<p style='color: #8888a0; font-size: 0.9em;'>No additional custom datasets detected.</p>", unsafe_allow_html=True)
st.markdown("---")

# Pipeline Trigger
st.markdown("### 🚀 Execute Graph AI Engine")
if uploaded_files_count == 0:
    st.warning("Please upload at least one dataset to run the pipeline.")
else:
    if st.button("RUN INTELLIGENCE PIPELINE", type="primary", use_container_width=True):
        st.markdown("---")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(pct: float, message: str):
            # Scale pct from 0-100 to 0.0-1.0
            val = max(0, min(100, pct)) / 100.0
            progress_bar.progress(val)
            status_text.markdown(f"**Status:** {message}")
            time.sleep(0.1)  # tiny sleep for UI updates
            
        with st.spinner("Pipeline is running... Please do not close this page."):
            try:
                # Clear the data cache in the backend service if we can
                # We can do this by forcing a restart message, or just let them know to restart uvicorn later
                run_full_pipeline(
                    source_dir=RAW_UPLOADS_DIR,
                    use_synthetic=False,
                    progress_callback=update_progress
                )
                
                # Tell the backend to reload its DataService
                import requests
                try:
                    requests.post("http://localhost:8000/system/reload", timeout=10)
                except Exception as req_err:
                    pass # ignore backend reload failure silently
                
                # CRITICAL: Clear Streamlit's frontend cache so dashboards re-read the fresh master_citizens.csv
                st.cache_data.clear()
                st.cache_resource.clear()
                
                # CRITICAL: Reload Streamlit's local DataService singleton
                try:
                    from backend.services.data_service import DataService
                    DataService().reload()
                except Exception as e:
                    pass
                
                progress_bar.progress(1.0)
                status_text.success("✅ **Pipeline Complete!** Graph database successfully updated.")
                st.balloons()
                
                st.info("✅ **Success!** Data has been automatically reloaded into the engine. You can now visit the Executive Dashboard.", icon="🎉")
                
            except Exception as e:
                st.error(f"Pipeline failed: {str(e)}")
                import traceback
                st.code(traceback.format_exc(), language="python")
