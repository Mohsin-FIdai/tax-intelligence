"""
Investigation Center — Global search, advanced filtering, and bulk investigation tools.
"""
import sys, io
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import PROCESSED_DIR, RISK_CATEGORIES


@st.cache_data
def load_citizens():
    try:
        return pd.read_csv(PROCESSED_DIR / "master_citizens.csv")
    except FileNotFoundError:
        return None


def _risk_pill(cat):
    info = RISK_CATEGORIES.get(str(cat), {"label": str(cat), "color": "#8888a0"})
    return f"{info.get('emoji', '⚪')} {info['label']}"


st.markdown("## 🔎 Investigation Center")
st.markdown('<p style="color:#8888a0;">Search, filter, and investigate citizens across the national database</p>',
            unsafe_allow_html=True)

citizens = load_citizens()
if citizens is None:
    st.warning("⚠️ No data found.")
    st.stop()

# ── Global Search ─────────────────────────────────────────────────
search_col, type_col, btn_col = st.columns([4, 1, 1])
with type_col:
    search_type = st.selectbox("Type", ["Name", "CNIC", "Phone", "City", "Citizen ID"],
                                label_visibility="collapsed")
with search_col:
    search_query = st.text_input("🔍 Search", placeholder=f"Search by {search_type}...",
                                  label_visibility="collapsed")

# ── Advanced Filters ──────────────────────────────────────────────
with st.expander("🎛️ Advanced Filters", expanded=False):
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        provinces = ["All"] + sorted(citizens["province"].dropna().unique().tolist()) if "province" in citizens.columns else ["All"]
        sel_province = st.selectbox("Province", provinces)
    with fc2:
        risk_levels = ["All"] + list(RISK_CATEGORIES.keys())
        sel_risk = st.selectbox("Risk Category", risk_levels,
                                format_func=lambda x: x if x == "All" else f"Cat {x}: {RISK_CATEGORIES[x]['label']}")
    with fc3:
        if "deviation_score" in citizens.columns:
            min_score, max_score = st.slider("Deviation Score", 0, 100, (0, 100))
        else:
            min_score, max_score = 0, 100
    with fc4:
        if "filing_status" in citizens.columns:
            filing_options = ["All"] + sorted(citizens["filing_status"].dropna().unique().tolist())
            sel_filing = st.selectbox("Filing Status", filing_options)
        else:
            sel_filing = "All"

    fc5, fc6 = st.columns(2)
    with fc5:
        if "declared_income" in citizens.columns and not citizens["declared_income"].isna().all():
            max_inc_val = citizens["declared_income"].max()
            max_income = int(max_inc_val) + 1 if pd.notna(max_inc_val) else 50_000_000
            income_range = st.slider("Income Range (PKR)", 0, min(max_income, 50_000_000),
                                     (0, min(max_income, 50_000_000)))
        else:
            income_range = (0, 50_000_000)
    with fc6:
        if "estimated_net_worth" in citizens.columns and not citizens["estimated_net_worth"].isna().all():
            max_nw_val = citizens["estimated_net_worth"].max()
            max_nw = int(max_nw_val) + 1 if pd.notna(max_nw_val) else 500_000_000
            nw_range = st.slider("Net Worth Range (PKR)", 0, min(max_nw, 500_000_000),
                                  (0, min(max_nw, 500_000_000)))
        else:
            nw_range = (0, 500_000_000)

# ── Apply Filters ─────────────────────────────────────────────────
filtered = citizens.copy()

# Search
if search_query:
    col_map = {
        "Name": "canonical_name", "CNIC": "cnic", "Phone": "phone",
        "City": "city", "Citizen ID": "citizen_id"
    }
    search_col_name = col_map.get(search_type, "canonical_name")
    
    try:
        from core.entity_resolution.intelligent_search import advanced_fuzzy_search
        # We need to preserve the dataframe but filter it. advanced_fuzzy_search returns the filtered dataframe.
        # But wait, advanced_fuzzy_search uses limit=10 by default! We should use a larger limit for the investigation center.
        filtered = advanced_fuzzy_search(filtered, search_query, search_columns=[search_col_name], limit=5000)
    except Exception as e:
        st.error(f"Search failed: {e}")
        filtered = pd.DataFrame(columns=filtered.columns)

# Filters
if sel_province != "All" and "province" in filtered.columns:
    filtered = filtered[filtered["province"] == sel_province]
if sel_risk != "All" and "risk_category" in filtered.columns:
    filtered = filtered[filtered["risk_category"] == sel_risk]
if "deviation_score" in filtered.columns:
    filtered = filtered[(filtered["deviation_score"] >= min_score) & (filtered["deviation_score"] <= max_score)]
if sel_filing != "All" and "filing_status" in filtered.columns:
    filtered = filtered[filtered["filing_status"] == sel_filing]
if "declared_income" in filtered.columns:
    filtered = filtered[(filtered["declared_income"] >= income_range[0]) & (filtered["declared_income"] <= income_range[1])]
if "estimated_net_worth" in filtered.columns:
    filtered = filtered[(filtered["estimated_net_worth"] >= nw_range[0]) & (filtered["estimated_net_worth"] <= nw_range[1])]

# ── Results Header ────────────────────────────────────────────────
st.markdown("---")
res_col1, res_col2 = st.columns([2, 1])
with res_col1:
    st.markdown(f"#### Results: **{len(filtered):,}** citizens found")
with res_col2:
    # Pagination
    page_size = st.selectbox("Per page", [25, 50, 100], index=0, label_visibility="collapsed")

total_pages = max(1, (len(filtered) - 1) // page_size + 1)
if "inv_page" not in st.session_state:
    st.session_state.inv_page = 0

pc1, pc2, pc3 = st.columns([1, 2, 1])
with pc1:
    if st.button("◀ Previous") and st.session_state.inv_page > 0:
        st.session_state.inv_page -= 1
with pc3:
    if st.button("Next ▶") and st.session_state.inv_page < total_pages - 1:
        st.session_state.inv_page += 1
with pc2:
    st.markdown(f"<div style='text-align:center; color:#8888a0;'>Page {st.session_state.inv_page + 1} of {total_pages}</div>",
                unsafe_allow_html=True)

# ── Results Table ─────────────────────────────────────────────────
start = st.session_state.inv_page * page_size
page_data = filtered.iloc[start:start + page_size].copy()

display_cols = ["canonical_name", "cnic", "city", "province", "filing_status",
                "declared_income", "estimated_net_worth", "deviation_score", "risk_category"]
display_cols = [c for c in display_cols if c in page_data.columns]
display_df = page_data[display_cols].copy()

# Format columns
col_rename = {
    "canonical_name": "Name", "cnic": "CNIC", "city": "City", "province": "Province",
    "filing_status": "Filing", "declared_income": "Income (PKR)",
    "estimated_net_worth": "Net Worth (PKR)", "deviation_score": "Score", "risk_category": "Risk"
}
display_df = display_df.rename(columns=col_rename)

for col in ["Income (PKR)", "Net Worth (PKR)"]:
    if col in display_df.columns:
        display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
if "Score" in display_df.columns:
    display_df["Score"] = display_df["Score"].round(1)
if "Risk" in display_df.columns:
    display_df["Risk"] = display_df["Risk"].apply(lambda x: _risk_pill(x))

st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

# ── Export Buttons ────────────────────────────────────────────────
st.markdown("---")
exp1, exp2, exp3 = st.columns(3)
with exp1:
    csv = filtered[display_cols].to_csv(index=False).encode("utf-8") if len(display_cols) > 0 else b""
    st.download_button("📥 Export CSV", csv, "investigation_results.csv", "text/csv",
                       use_container_width=True)
with exp2:
    buf = io.BytesIO()
    if len(display_cols) > 0:
        filtered[display_cols].to_excel(buf, index=False, engine="openpyxl")
    st.download_button("📥 Export Excel", buf.getvalue(), "investigation_results.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)
with exp3:
    if st.button("📄 Generate PDF Report", use_container_width=True):
        try:
            from core.reports.pdf_generator import PDFReportGenerator
            gen = PDFReportGenerator()
            cit_list = filtered.head(50).to_dict("records")
            path = gen.generate_investigation_report(cit_list)
            st.success(f"✅ Report saved: {path}")
        except Exception as e:
            st.error(f"Failed: {e}")
