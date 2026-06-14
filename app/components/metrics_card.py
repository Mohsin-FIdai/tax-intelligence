"""
Reusable KPI Metric Card Component
Renders glassmorphism cards with icon, title, large value, and optional delta.
"""
import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    delta: str = None,
    delta_color: str = "normal",
    icon: str = "📊",
    color: str = "#00d4aa",
    anim_delay: int = 0,
):
    """
    Render a premium KPI metric card.

    Args:
        title: Label above the value
        value: Large display value (pre-formatted string)
        delta: Optional delta text (e.g. "+12%")
        delta_color: 'normal' (green), 'inverse' (red), or 'off' (grey)
        icon: Emoji icon
        color: Accent color for the top gradient bar
        anim_delay: Animation delay index (1-6) for staggered appearance
    """
    delta_class = {
        "normal": "positive",
        "inverse": "negative",
        "off": "neutral",
    }.get(delta_color, "neutral")

    delta_html = ""
    if delta is not None:
        arrow = ""
        if delta_class == "positive":
            arrow = "▲ "
        elif delta_class == "negative":
            arrow = "▼ "
        delta_html = f'<div class="kpi-delta {delta_class}">{arrow}{delta}</div>'

    delay_class = f"anim-delay-{anim_delay}" if anim_delay else ""

    # Determine gradient for the top bar
    gradient = f"linear-gradient(90deg, {color}, {_shift_hue(color)})"

    st.markdown(
        f"""
        <div class="kpi-card {delay_class}" style="--card-accent: {color};">
            <style>
                .kpi-card[style*="--card-accent: {color}"]::before {{
                    background: {gradient} !important;
                }}
            </style>
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_row(metrics: list):
    """
    Render a row of KPI cards evenly spaced.

    Args:
        metrics: List of dicts with keys matching render_metric_card params
    """
    cols = st.columns(len(metrics))
    for idx, (col, m) in enumerate(zip(cols, metrics)):
        with col:
            render_metric_card(
                title=m.get("title", ""),
                value=m.get("value", "0"),
                delta=m.get("delta"),
                delta_color=m.get("delta_color", "normal"),
                icon=m.get("icon", "📊"),
                color=m.get("color", "#00d4aa"),
                anim_delay=idx + 1,
            )


def _shift_hue(hex_color: str) -> str:
    """Create a slightly shifted version of a hex color for gradient end."""
    mapping = {
        "#00d4aa": "#4a9eff",
        "#4a9eff": "#7b68ee",
        "#ff3355": "#ff8c00",
        "#ffd000": "#ff8c00",
        "#ff8c00": "#ff3355",
    }
    return mapping.get(hex_color, "#4a9eff")
