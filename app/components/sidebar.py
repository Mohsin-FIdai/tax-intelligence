"""
Global Sidebar Component
Renders branding, global filters (province, city, risk level, search).
Returns a filter state dictionary for use by pages.
"""
import sys
from pathlib import Path

import streamlit as st

# Ensure config is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import PROVINCES, CITIES_BY_PROVINCE, RISK_CATEGORIES, THEME


def render_sidebar() -> dict:
    """
    Render the global sidebar with branding and filters.

    Returns:
        Dictionary of filter values:
            {
                "province": list[str],
                "city": list[str],
                "risk_level": list[str],
                "search_query": str,
            }
    """
    with st.sidebar:
        # ── Branding ─────────────────────────────────────────────────
        st.markdown(
            """
            <div style="text-align:center;padding:0.5rem 0 1.2rem;">
                <div style="font-size:2rem;margin-bottom:2px;">🏛️</div>
                <div style="font-size:1.1rem;font-weight:800;color:#e8e8ed;letter-spacing:-0.02em;">
                    Tax Intelligence
                </div>
                <div style="font-size:0.68rem;color:#00d4aa;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.12em;margin-top:2px;">
                    Pakistan • Graph AI Platform
                </div>
            </div>
            <hr style="border-color:#2a2a3e;margin:0 0 1rem;">
            """,
            unsafe_allow_html=True,
        )

        # ── Global Filters ───────────────────────────────────────────
        st.markdown(
            '<div style="color:#8888a0;font-size:0.7rem;font-weight:700;text-transform:uppercase;'
            'letter-spacing:0.1em;margin-bottom:8px;">🔍 Global Filters</div>',
            unsafe_allow_html=True,
        )

        # Search
        search_query = st.text_input(
            "Search",
            placeholder="CNIC, Name, or ID...",
            label_visibility="collapsed",
        )

        # Province filter
        province_options = list(PROVINCES.keys())
        selected_provinces = st.multiselect(
            "Province",
            options=province_options,
            default=[],
            placeholder="All Provinces",
        )

        # City filter — dynamic based on province selection
        if selected_provinces:
            city_options = []
            for prov in selected_provinces:
                city_options.extend(CITIES_BY_PROVINCE.get(prov, []))
        else:
            city_options = []
            for cities in CITIES_BY_PROVINCE.values():
                city_options.extend(cities)
        city_options = sorted(set(city_options))

        selected_cities = st.multiselect(
            "City",
            options=city_options,
            default=[],
            placeholder="All Cities",
        )

        # Risk level filter
        risk_options = [f'{k} — {v["label"]}' for k, v in RISK_CATEGORIES.items()]
        selected_risks = st.multiselect(
            "Risk Category",
            options=risk_options,
            default=[],
            placeholder="All Risk Levels",
        )
        # Extract category keys
        selected_risk_keys = [r.split(" — ")[0] for r in selected_risks]

        # ── Separator ────────────────────────────────────────────────
        st.markdown("<hr style='border-color:#2a2a3e;margin:1rem 0;'>", unsafe_allow_html=True)

        # ── System Info ──────────────────────────────────────────────
        st.markdown(
            """
            <div style="color:#55556a;font-size:0.68rem;text-align:center;line-height:1.6;">
                <div>Graph AI Engine v2.0</div>
                <div>Built with Streamlit + Plotly + PyVis</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return {
        "province": selected_provinces,
        "city": selected_cities,
        "risk_level": selected_risk_keys,
        "search_query": search_query.strip(),
    }


def apply_filters(df, filters: dict):
    """
    Apply sidebar filters to a DataFrame.

    Args:
        df: Pandas DataFrame with columns like province, city, risk_category, name, cnic
        filters: Dict from render_sidebar()

    Returns:
        Filtered DataFrame
    """
    import pandas as pd

    if df is None or df.empty:
        return df

    filtered = df.copy()

    # Province filter
    if filters.get("province"):
        if "province" in filtered.columns:
            filtered = filtered[filtered["province"].isin(filters["province"])]

    # City filter
    if filters.get("city"):
        if "city" in filtered.columns:
            filtered = filtered[filtered["city"].isin(filters["city"])]

    # Risk level filter
    if filters.get("risk_level"):
        if "risk_category" in filtered.columns:
            filtered = filtered[filtered["risk_category"].isin(filters["risk_level"])]

    # Search query
    query = filters.get("search_query", "")
    if query:
        mask = pd.Series([False] * len(filtered), index=filtered.index)
        for col in ["cnic", "name", "full_name", "citizen_id"]:
            if col in filtered.columns:
                mask = mask | filtered[col].astype(str).str.contains(query, case=False, na=False)
        filtered = filtered[mask]

    return filtered
