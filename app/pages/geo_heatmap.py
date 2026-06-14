"""
Geographic Tax-Evasion Heat Maps
"""
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.data_service import DataService
from app.pages.executive_dashboard import _plotly_layout

st.set_page_config(page_title="Geographic Intelligence", page_icon="🗺️", layout="wide")

st.markdown("## 🗺️ Geographic Tax-Evasion Heat Maps")
st.markdown('<p style="color:#8888a0;">Visualising fraud clusters and high-risk regions across Pakistan</p>', unsafe_allow_html=True)

@st.cache_data
def load_geo_data():
    svc = DataService()
    if not svc.is_loaded:
        return None, None
        
    try:
        travel_df = pd.read_csv("data/synthetic/travel_records.csv")
    except Exception:
        travel_df = None
        
    return svc.citizens_df, travel_df

citizens, travel_df = load_geo_data()
if citizens is None or "city" not in citizens.columns:
    st.warning("⚠️ No geographical data loaded.")
    st.stop()

# Pakistan City Coordinates for Mapping
CITY_COORDS = {
    "Karachi": {"lat": 24.8607, "lon": 67.0011},
    "Lahore": {"lat": 31.5497, "lon": 74.3436},
    "Islamabad": {"lat": 33.6844, "lon": 73.0479},
    "Rawalpindi": {"lat": 33.5909, "lon": 73.0537},
    "Peshawar": {"lat": 34.0151, "lon": 71.5249},
    "Quetta": {"lat": 30.1798, "lon": 66.9750},
    "Multan": {"lat": 30.1575, "lon": 71.5249},
    "Faisalabad": {"lat": 31.4504, "lon": 73.1350},
    "Gujranwala": {"lat": 32.1617, "lon": 74.1883},
    "Sialkot": {"lat": 32.4945, "lon": 74.5229},
    "Hyderabad": {"lat": 25.3960, "lon": 68.3578},
    "Sukkur": {"lat": 27.7052, "lon": 68.8574},
}

# Aggregate by city
if "estimated_hidden_income" in citizens.columns:
    geo_df = citizens.groupby("city").agg(
        Total_Citizens=("citizen_id", "count"),
        High_Risk_Count=("risk_category", lambda x: (x.isin(["D", "E"])).sum()),
        Avg_Deviation_Score=("deviation_score", "mean"),
        Total_Hidden_Income=("estimated_hidden_income", "sum")
    ).reset_index()
    
    # Map coordinates
    geo_df["lat"] = geo_df["city"].map(lambda c: CITY_COORDS.get(c, {}).get("lat", 30.0))
    geo_df["lon"] = geo_df["city"].map(lambda c: CITY_COORDS.get(c, {}).get("lon", 70.0))
    
    # Drop unknown cities for the map
    map_df = geo_df[geo_df["city"].isin(CITY_COORDS.keys())].copy()
    
    if len(map_df) > 0:
        fig = px.scatter_mapbox(
            map_df, 
            lat="lat", lon="lon", 
            size="Total_Hidden_Income", 
            color="High_Risk_Count",
            color_continuous_scale="Reds",
            size_max=50,
            zoom=4.5,
            mapbox_style="carto-darkmatter",
            hover_name="city",
            hover_data={"lat": False, "lon": False, "Total_Hidden_Income": ":,.0f", "High_Risk_Count": True},
            title="Pakistan Fraud Clusters (Sized by Hidden Income, Colored by Risk)"
        )
        fig.update_layout(
            margin={"r":0,"t":40,"l":0,"b":0},
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8e8ed")
        )
        st.plotly_chart(fig, use_container_width=True)
        
    # Top 10 Countries Map
    if travel_df is not None and "destination" in travel_df.columns:
        st.markdown("---")
        st.markdown("### ✈️ Top 10 International Destinations for High-Risk Individuals")
        merged = pd.merge(travel_df, citizens[["cnic", "risk_category"]], on="cnic", how="inner")
        high_risk_travel = merged[merged["risk_category"].isin(["D", "E"])]
        if not high_risk_travel.empty:
            dest_counts = high_risk_travel["destination"].value_counts().head(10).reset_index()
            dest_counts.columns = ["Country", "Visits"]
            
            fig2 = px.choropleth(
                dest_counts,
                locations="Country",
                locationmode="country names",
                color="Visits",
                color_continuous_scale="Reds",
                title="Top 10 High-Risk Destinations"
            )
            fig2.update_geos(
                visible=False, resolution=110,
                showcountries=True, countrycolor="#444444",
                showcoastlines=True, coastlinecolor="#444444",
                showland=True, landcolor="#1e1e1e",
                showocean=True, oceancolor="#0a0a0f"
            )
            fig2.update_layout(
                margin={"r":0,"t":40,"l":0,"b":0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8e8ed")
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No international travel data available for high-risk citizens.")
    
    # Show data table
    st.markdown("### 📍 Top High-Risk Regions")
    geo_df = geo_df.sort_values("Total_Hidden_Income", ascending=False)
    
    def format_pkr(val):
        if val > 1e9: return f"{val/1e9:.1f}B"
        if val > 1e6: return f"{val/1e6:.1f}M"
        return f"{val:,.0f}"
        
    display_df = geo_df.copy()
    display_df["Total_Hidden_Income"] = display_df["Total_Hidden_Income"].apply(format_pkr)
    display_df["Avg_Deviation_Score"] = display_df["Avg_Deviation_Score"].round(1)
    
    st.dataframe(display_df[["city", "Total_Citizens", "High_Risk_Count", "Avg_Deviation_Score", "Total_Hidden_Income"]], 
                 use_container_width=True, hide_index=True)
else:
    st.info("Tax Gap data not computed yet. Run pipeline first.")
