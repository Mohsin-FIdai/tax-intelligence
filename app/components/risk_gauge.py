"""
Risk Gauge Component
Plotly gauge chart for risk scores with color-coded bands.
"""
import plotly.graph_objects as go


def render_risk_gauge(score: float, title: str = "Risk Score", height: int = 250) -> go.Figure:
    """
    Create a Plotly gauge chart for risk scores.

    Args:
        score: Risk score 0–100
        title: Chart title
        height: Chart height in pixels

    Returns:
        Plotly Figure object
    """
    score = max(0, min(100, score))

    # Determine color based on score
    if score <= 20:
        needle_color = "#00d4aa"
        label = "Compliant"
    elif score <= 40:
        needle_color = "#4a9eff"
        label = "Needs Review"
    elif score <= 60:
        needle_color = "#ffd000"
        label = "Suspicious"
    elif score <= 80:
        needle_color = "#ff8c00"
        label = "Likely Evader"
    else:
        needle_color = "#ff3355"
        label = "Critical"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=score,
            number={
                "font": {"size": 42, "color": needle_color, "family": "Inter"},
                "suffix": "",
            },
            title={
                "text": f"<b>{title}</b><br><span style='font-size:0.75em;color:#8888a0'>{label}</span>",
                "font": {"size": 14, "color": "#e8e8ed", "family": "Inter"},
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": "#2a2a3e",
                    "dtick": 20,
                    "tickfont": {"color": "#8888a0", "size": 10},
                },
                "bar": {"color": needle_color, "thickness": 0.25},
                "bgcolor": "#12121a",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 20], "color": "rgba(0, 212, 170, 0.12)"},
                    {"range": [20, 40], "color": "rgba(74, 158, 255, 0.12)"},
                    {"range": [40, 60], "color": "rgba(255, 208, 0, 0.12)"},
                    {"range": [60, 80], "color": "rgba(255, 140, 0, 0.12)"},
                    {"range": [80, 100], "color": "rgba(255, 51, 85, 0.12)"},
                ],
                "threshold": {
                    "line": {"color": needle_color, "width": 3},
                    "thickness": 0.85,
                    "value": score,
                },
            },
        )
    )

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter", "color": "#e8e8ed"},
    )

    return fig
