"""
Citizen Profile — Deep-dive view for individual citizens with assets, risk, and audit trail.
"""
import sys, pickle
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import PROCESSED_DIR, MODELS_DIR, RISK_CATEGORIES, REPORTS_DIR
from backend.services.data_service import DataService


@st.cache_data
def load_citizens():
    try:
        return pd.read_csv(PROCESSED_DIR / "master_citizens.csv")
    except FileNotFoundError:
        return None


def _risk_badge(cat):
    info = RISK_CATEGORIES.get(cat, {"label": cat, "color": "#8888a0", "emoji": "⚪"})
    return f'<span style="background:{info["color"]}22; color:{info["color"]}; padding:0.2rem 0.8rem; border-radius:20px; font-size:0.85rem; font-weight:600; border:1px solid {info["color"]}44;">{info["emoji"]} {info["label"]}</span>'


def _filing_badge(status):
    colors = {"Filed": "#00d4aa", "Non-Filer": "#ff3355", "Late Filer": "#ffd000"}
    c = colors.get(str(status).strip(), "#8888a0")
    return f'<span style="background:{c}22; color:{c}; padding:0.2rem 0.6rem; border-radius:12px; font-size:0.75rem; border:1px solid {c}44;">{status}</span>'


def _fmt(val):
    try:
        v = float(val)
        if v >= 1e7:
            return f"PKR {v/1e7:,.2f} Cr"
        if v >= 1e5:
            return f"PKR {v/1e5:,.1f} L"
        return f"PKR {v:,.0f}"
    except (ValueError, TypeError):
        return str(val)


st.markdown("## 👤 Citizen Profile")
st.markdown('<p style="color:#8888a0;">Comprehensive profile view with assets, risk assessment, and audit trail</p>',
            unsafe_allow_html=True)

citizens = load_citizens()
if citizens is None:
    st.warning("⚠️ No data found.")
    st.stop()

# ── Search ────────────────────────────────────────────────────────
search_col, type_col = st.columns([3, 1])
with type_col:
    search_type = st.selectbox("Search by", ["Name", "CNIC", "Citizen ID"], label_visibility="collapsed")
with search_col:
    query = st.text_input("Search citizen...", placeholder="Enter name, CNIC, or ID")

if query:
    try:
        from core.entity_resolution.intelligent_search import advanced_fuzzy_search
        
        if search_type == "CNIC":
            matches = advanced_fuzzy_search(citizens, query, search_columns=["cnic"])
        elif search_type == "Citizen ID":
            matches = advanced_fuzzy_search(citizens, query, search_columns=["citizen_id"])
        else:
            matches = advanced_fuzzy_search(citizens, query, search_columns=["canonical_name"])
    except Exception as e:
        st.error(f"Search failed: {e}")
        matches = pd.DataFrame(columns=citizens.columns)
    if len(matches) == 0:
        st.warning("No citizens found matching your search.")
        st.stop()
    elif len(matches) > 1:
        selected_idx = st.selectbox("Multiple matches found — select one:",
                                     matches.index.tolist(),
                                     format_func=lambda i: f"{matches.loc[i, 'canonical_name']} ({matches.loc[i, 'cnic']})")
        citizen = matches.loc[selected_idx]
    else:
        citizen = matches.iloc[0]
else:
    st.info("👆 Search for a citizen above, or select from the top risk cases below:")
    if "deviation_score" in citizens.columns:
        top = citizens.nlargest(10, "deviation_score")
        selected_idx = st.selectbox("Top Risk Citizens",
                                     top.index.tolist(),
                                     format_func=lambda i: f"{top.loc[i, 'canonical_name']} — Score: {top.loc[i, 'deviation_score']:.0f}")
        citizen = citizens.loc[selected_idx]
    else:
        citizen = citizens.iloc[0]

# ── Profile Header ────────────────────────────────────────────────
st.markdown("---")
name = citizen.get("canonical_name", "Unknown")
cnic = citizen.get("cnic", "N/A")
city = citizen.get("city", "N/A")
province = citizen.get("province", "N/A")
filing = citizen.get("filing_status", "N/A")
risk_cat = citizen.get("risk_category", "C")
dev_score = float(citizen.get("deviation_score", 0))

st.markdown(f"""
<div style="background:#1a1a2e; border-radius:12px; padding:1.5rem; border:1px solid #2a2a3e;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
        <div>
            <h2 style="margin:0; color:#e8e8ed;">{name}</h2>
            <p style="color:#8888a0; margin:0.3rem 0;">CNIC: <code>{cnic}</code> &nbsp;|&nbsp; {city}, {province}</p>
            <div style="margin-top:0.5rem;">{_filing_badge(filing)} &nbsp; {_risk_badge(risk_cat)}</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:2.5rem; font-weight:800; color:{'#ff3355' if dev_score > 70 else '#ffd000' if dev_score > 40 else '#00d4aa'};">
                {dev_score:.0f}
            </div>
            <div style="font-size:0.7rem; color:#8888a0; text-transform:uppercase;">Deviation Score</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Risk Gauge + Financial Summary ────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=dev_score,
        title={"text": "Risk Score", "font": {"size": 14, "color": "#e8e8ed"}},
        number={"font": {"size": 36, "color": "#e8e8ed"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#8888a0"},
            "bar": {"color": RISK_CATEGORIES.get(risk_cat, {}).get("color", "#ffd000")},
            "bgcolor": "#1a1a2e",
            "bordercolor": "#2a2a3e",
            "steps": [
                {"range": [0, 20], "color": "rgba(0, 212, 170, 0.15)"},
                {"range": [20, 40], "color": "rgba(74, 158, 255, 0.15)"},
                {"range": [40, 60], "color": "rgba(255, 208, 0, 0.15)"},
                {"range": [60, 80], "color": "rgba(255, 140, 0, 0.15)"},
                {"range": [80, 100], "color": "rgba(255, 51, 85, 0.15)"},
            ],
        },
    ))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      height=250, margin=dict(l=20, r=20, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True, theme=None)

with col2:
    income = float(citizen.get("declared_income", 0))
    net_worth = float(citizen.get("estimated_net_worth", 0))
    tax_paid = float(citizen.get("tax_paid", 0))
    prop_val = float(citizen.get("total_property_value", 0))
    veh_val = float(citizen.get("total_vehicle_value", 0))

    fig = go.Figure()
    cats = ["Declared Income", "Tax Paid", "Vehicle Value", "Property Value", "Est. Net Worth"]
    vals = [income, tax_paid, veh_val, prop_val, net_worth]
    colors = ["#4a9eff", "#00d4aa", "#ffd000", "#ff8c00", "#ff3355"]
    fig.add_trace(go.Bar(y=cats, x=vals, orientation="h",
                         marker_color=colors, text=[_fmt(v) for v in vals],
                         textposition="auto"))
    fig.update_layout(title="Financial Overview", template="plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=250, margin=dict(l=10, r=10, t=40, b=10),
                      font=dict(color="#e8e8ed"),
                      xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True, theme=None)

# ── Risk Timeline ─────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### ⏳ Citizen Risk Timeline")

# Build timeline events from datasets
timeline_events = []
svc = DataService()

# Tax records
if hasattr(svc, "tax_records_df") and "tax_year" in svc.tax_records_df.columns:
    user_tax = svc.tax_records_df[svc.tax_records_df["cnic"] == cnic]
    for _, row in user_tax.iterrows():
        timeline_events.append({"Year": int(row["tax_year"]), "Event": f"Filed Tax Return (Declared: {_fmt(row.get('declared_income', 0))})", "Type": "Tax", "Color": "#00d4aa"})

# Vehicles
if hasattr(svc, "vehicles_df") and "vehicle_year" in svc.vehicles_df.columns:
    user_veh = svc.vehicles_df[svc.vehicles_df["cnic"] == cnic]
    for _, row in user_veh.iterrows():
        year = int(row["vehicle_year"]) if pd.notna(row["vehicle_year"]) else 2023
        timeline_events.append({"Year": year, "Event": f"Registered {row.get('vehicle_make', 'Vehicle')} (Value: {_fmt(row.get('market_value', 0))})", "Type": "Asset", "Color": "#ff8c00"})

# Travel (use year from departure_date if exists, else assign recent year)
if hasattr(svc, "travel_records_df") and "departure_date" in svc.travel_records_df.columns:
    user_travel = svc.travel_records_df[svc.travel_records_df["cnic"] == cnic]
    for _, row in user_travel.iterrows():
        try:
            year = pd.to_datetime(row["departure_date"]).year
        except:
            year = 2023
        timeline_events.append({"Year": year, "Event": f"Traveled to {row.get('destination', 'Unknown')} ({row.get('airline', '')})", "Type": "Travel", "Color": "#4a9eff"})

if timeline_events:
    timeline_df = pd.DataFrame(timeline_events).sort_values("Year", ascending=False)
    
    for _, row in timeline_df.iterrows():
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom: 10px;">
            <div style="width: 60px; font-weight: bold; color: {row['Color']};">{row['Year']}</div>
            <div style="width: 15px; height: 15px; border-radius: 50%; background-color: {row['Color']}; margin-right: 15px;"></div>
            <div style="flex-grow: 1; padding: 10px; background: #1a1a2e; border-left: 3px solid {row['Color']}; border-radius: 4px;">
                {row['Event']}
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No timeline events found for this citizen.")

# ── Audit Trail ───────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📋 Audit Trail")

# Generate audit trail from citizen data
flags = []
if prop_val > 0:
    sev = "CRITICAL" if prop_val > 20e6 else "WARNING"
    flags.append(("🔴" if sev == "CRITICAL" else "🟠", f"Owns property worth {_fmt(prop_val)}", sev))
if veh_val > 0:
    sev = "CRITICAL" if veh_val > 10e6 else "WARNING" if veh_val > 3e6 else "INFO"
    icon = "🔴" if sev == "CRITICAL" else "🟠" if sev == "WARNING" else "🔵"
    flags.append((icon, f"Owns vehicle(s) worth {_fmt(veh_val)}", sev))
if income < 600_000 and net_worth > 5e6:
    flags.append(("🔴", f"Declared income only {_fmt(income)} vs net worth {_fmt(net_worth)}", "CRITICAL"))
if tax_paid == 0 and net_worth > 2e6:
    flags.append(("🔴", "No tax paid despite significant assets", "CRITICAL"))
if str(filing).lower() in ("non-filer", ""):
    flags.append(("🔴", "Non-filer — no tax return filed", "CRITICAL"))

travel_count = float(citizen.get("foreign_travel_count", 0))
if travel_count > 2:
    flags.append(("🟠", f"{int(travel_count)} international trips recorded", "WARNING"))

biz_count = float(citizen.get("business_count", 0))
if biz_count > 0:
    flags.append(("🟠", f"Director/owner of {int(biz_count)} company(ies)", "WARNING"))

if income > 0 and net_worth > 0:
    ratio = income / net_worth
    if ratio < 0.15:
        flags.append(("🔴", f"Income-to-Asset ratio: {ratio:.3f} (threshold: 0.15)", "CRITICAL"))

for icon, desc, sev in flags:
    bg = "#ff335510" if sev == "CRITICAL" else "#ff8c0010" if sev == "WARNING" else "#4a9eff10"
    st.markdown(f"""
    <div style="background:{bg}; border-left:3px solid {'#ff3355' if sev == 'CRITICAL' else '#ff8c00' if sev == 'WARNING' else '#4a9eff'};
                padding:0.5rem 1rem; margin:0.3rem 0; border-radius:0 8px 8px 0;">
        {icon} &nbsp; {desc}
    </div>
    """, unsafe_allow_html=True)

if not flags:
    st.success("✅ No significant flags detected for this citizen.")

# ── Action buttons ────────────────────────────────────────────────
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📄 Generate PDF Report", use_container_width=True, type="primary"):
        try:
            from core.reports.pdf_generator import PDFReportGenerator
            gen = PDFReportGenerator()
            profile = citizen.to_dict()
            risk_result = {"deviation_score": dev_score, "risk_category": risk_cat}
            audit = {"flags": [{"description": d, "severity": s} for _, d, s in flags],
                     "summary": f"Risk assessment for {name}", "confidence": 85,
                     "recommendations": ["Review asset disclosures"]}
            path = gen.generate_citizen_report(profile, risk_result, audit)
            st.success(f"✅ Report generated: {path}")
        except Exception as e:
            st.error(f"Report generation failed: {e}")
with col2:
    if st.button("🚩 Flag for Investigation", use_container_width=True):
        st.success(f"🚩 {name} flagged for investigation.")
with col3:
    if st.button("📊 View in Graph", use_container_width=True):
        st.info("Navigate to Knowledge Graph page and search for this citizen.")
