"""
Graph Viewer Component
PyVis-based interactive network graph embedding for Streamlit.
"""
import tempfile
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

try:
    import networkx as nx
    from pyvis.network import Network
except ImportError:
    nx = None
    Network = None


# Risk category colors
_NODE_TYPE_COLORS = {
    "citizen": "#00d4aa",
    "vehicle": "#4a9eff",
    "property": "#ffd000",
    "business": "#ff8c00",
    "phone": "#7b68ee",
    "address": "#ff3355",
    "bank_account": "#00b894",
    "default": "#8888a0",
}


def render_graph(
    G_networkx,
    height: int = 600,
    physics: bool = True,
    node_colors: dict = None,
    title: str = None,
):
    """
    Convert a NetworkX graph to a PyVis interactive visualization and embed in Streamlit.

    Args:
        G_networkx: NetworkX graph object
        height: Height of the embedded graph in pixels
        physics: Enable physics simulation
        node_colors: Optional dict mapping node_id → color hex string
        title: Optional title shown above the graph
    """
    if nx is None or Network is None:
        st.error("NetworkX and PyVis are required. Install with: pip install networkx pyvis")
        return

    if G_networkx is None or len(G_networkx.nodes()) == 0:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">🕸️</div>
                <div class="empty-title">No Graph Data</div>
                <div class="empty-detail">The graph is empty. Run the knowledge graph pipeline to generate connections.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if title:
        st.markdown(
            f"""<div class="section-header">
                <span class="section-icon">🕸️</span>
                <h3>{title}</h3>
            </div>""",
            unsafe_allow_html=True,
        )

    # Create PyVis network
    net = Network(
        height=f"{height}px",
        width="100%",
        bgcolor="#0a0a0f",
        font_color="#e8e8ed",
        directed=G_networkx.is_directed(),
    )

    # Physics configuration
    if physics:
        net.force_atlas_2based(
            gravity=-60,
            central_gravity=0.008,
            spring_length=120,
            spring_strength=0.04,
            damping=0.85,
            overlap=0.5,
        )
    else:
        net.toggle_physics(False)

    # Add nodes
    for node_id, attrs in G_networkx.nodes(data=True):
        node_type = attrs.get("type", attrs.get("node_type", "default"))
        label = attrs.get("label", attrs.get("name", str(node_id)))
        size = attrs.get("size", attrs.get("importance", 15))

        # Determine color
        if node_colors and node_id in node_colors:
            color = node_colors[node_id]
        else:
            color = _NODE_TYPE_COLORS.get(node_type, _NODE_TYPE_COLORS["default"])

        # Build tooltip
        tooltip_lines = [f"<b>{label}</b>", f"Type: {node_type}"]
        for k, v in attrs.items():
            if k not in ("label", "name", "type", "node_type", "size", "importance", "x", "y"):
                tooltip_lines.append(f"{k}: {v}")
        tooltip = "<br>".join(tooltip_lines)

        net.add_node(
            node_id,
            label=str(label)[:25],
            color=color,
            size=max(8, min(40, size)),
            title=tooltip,
            font={"size": 10, "color": "#e8e8ed", "face": "Inter"},
            borderWidth=1,
            borderWidthSelected=3,
        )

    # Add edges
    for src, dst, attrs in G_networkx.edges(data=True):
        edge_label = attrs.get("label", attrs.get("relationship", ""))
        weight = attrs.get("weight", 1)
        edge_color = attrs.get("color", "rgba(136, 136, 160, 0.3)")

        net.add_edge(
            src,
            dst,
            title=edge_label,
            width=max(0.5, min(4, weight)),
            color=edge_color,
            smooth={"type": "continuous"},
        )

    # Configure interaction
    net.set_options("""
    {
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": false,
            "keyboard": { "enabled": true }
        },
        "nodes": {
            "shape": "dot",
            "shadow": { "enabled": true, "size": 6, "color": "rgba(0,0,0,0.3)" }
        },
        "edges": {
            "smooth": { "type": "continuous" }
        }
    }
    """)

    # Save to temp file and embed
    tmp_dir = Path(tempfile.gettempdir()) / "tax_intel_graphs"
    tmp_dir.mkdir(exist_ok=True)
    tmp_file = tmp_dir / "graph_viewer.html"
    net.save_graph(str(tmp_file))

    # Read the generated HTML
    with open(tmp_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inject custom styles into the HTML
    custom_css = """
    <style>
        body { margin: 0; padding: 0; overflow: hidden; background: #0a0a0f; }
        #mynetwork { border: none !important; }
    </style>
    """
    html_content = html_content.replace("</head>", f"{custom_css}</head>")

    components.html(html_content, height=height + 20, scrolling=False)


def render_graph_legend(node_types: list = None):
    """Render a color legend for node types."""
    if node_types is None:
        node_types = list(_NODE_TYPE_COLORS.keys())
        node_types = [t for t in node_types if t != "default"]

    legend_items = []
    for nt in node_types:
        color = _NODE_TYPE_COLORS.get(nt, _NODE_TYPE_COLORS["default"])
        legend_items.append(
            f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:16px;">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{color};display:inline-block;"></span>'
            f'<span style="color:#8888a0;font-size:0.78rem;text-transform:capitalize;">{nt}</span></span>'
        )

    st.markdown(
        f'<div style="padding:8px 0;display:flex;flex-wrap:wrap;gap:4px;">{"".join(legend_items)}</div>',
        unsafe_allow_html=True,
    )
