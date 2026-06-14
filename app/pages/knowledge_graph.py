"""
Knowledge Graph Explorer — Interactive graph visualization and analytics.
"""
import sys, pickle, tempfile
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import networkx as nx
import plotly.express as px

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import PROCESSED_DIR, MODELS_DIR, THEME


@st.cache_resource
def load_graph(mtime=0):
    path = MODELS_DIR / "knowledge_graph.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


@st.cache_data
def load_citizens(mtime=0):
    try:
        return pd.read_csv(PROCESSED_DIR / "master_citizens.csv")
    except FileNotFoundError:
        return None

def get_logical_community_name(G, comm_nodes, focus=None):
    from collections import Counter
    if focus == "Company & Business Based":
        companies = [n for n in comm_nodes if G.nodes[n].get("node_type") == "Company"]
        if companies:
            biggest = max(companies, key=lambda x: G.degree(x))
            lbl = G.nodes[biggest].get("label", str(biggest))
            return f"{lbl} Corporate Group"
            
    if focus == "Financial & Banking Based":
        banks = [n for n in comm_nodes if G.nodes[n].get("node_type") == "Bank"]
        if banks:
            biggest = max(banks, key=lambda x: G.degree(x))
            lbl = G.nodes[biggest].get("label", str(biggest))
            return f"{lbl} Financial Network"

    if focus in ("City & Property Based", "Address & Property Based"):
        cities = []
        for n in comm_nodes:
            if G.nodes[n].get("node_type") in ["Person", "Property"]:
                city = G.nodes[n].get("city", "")
                if city and str(city).strip().lower() not in ["", "nan", "none", "unknown"]:
                    cities.append(str(city).strip().title())
        if cities:
            most_common = Counter(cities).most_common(1)[0][0]
            return f"{most_common} Region Cluster"

    # Fallback: prominent node
    max_deg = -1
    prominent_node = None
    for n in comm_nodes:
        deg = G.degree(n)
        if deg > max_deg:
            max_deg = deg
            prominent_node = n

    if prominent_node:
        ntype = G.nodes[prominent_node].get("node_type", "")
        lbl = G.nodes[prominent_node].get("label", str(prominent_node))
        if ntype == "Person":
            return f"{lbl} Network"
        elif ntype == "Company":
            return f"{lbl} Corporate Group"
        elif ntype == "Address":
            return f"{lbl[:20]} Cluster"
        elif ntype == "Bank":
            return f"{lbl} Financial Network"
        elif ntype == "Property":
            city = G.nodes[prominent_node].get("city", "")
            if city and str(city).lower() not in ["nan", "none"]:
                return f"{city.title()} Property Cluster"
            return f"{lbl} Property Cluster"
        else:
            return f"{lbl} Hub"
            
    return "Unnamed Community"


def render_pyvis_graph(subgraph, height=550):
    """Render a NetworkX subgraph as an interactive PyVis visualization."""
    try:
        from pyvis.network import Network
    except ImportError:
        st.error("PyVis is required. Install with: pip install pyvis")
        return

    net = Network(height=f"{height}px", width="100%", bgcolor="#0a0a0f",
                  font_color="#e8e8ed", directed=True)
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=100)

    for node_id, data in subgraph.nodes(data=True):
        label = data.get("label", str(node_id))[:25]
        color = data.get("color", "#00d4aa")
        ntype = data.get("node_type", "Unknown")
        size = 25 if ntype == "Person" else 15
        title = f"{label}\nType: {ntype}"
        if ntype == "Person":
            title += f"\nCNIC: {data.get('cnic', 'N/A')}"
            title += f"\nContact No: {data.get('contact_no', 'N/A')}"
            title += f"\nTax Status: {data.get('filing_status', 'Unknown')}"
            title += f"\nRisk: {data.get('risk_score', 0):.0f}"
        elif ntype == "BankAccount":
            title += f"\nBank: {data.get('bank_name', 'Bank')}"
            title += f"\nAccount No: {data.get('account_number', 'N/A')}"
            title += f"\nAvg Expenditure: {data.get('avg_expenditure', 0):,.0f}"
        elif ntype == "Property":
            title += f"\nProperty Type: {data.get('property_type', 'N/A')}"
            title += f"\nHouse/Plot No: {data.get('plot_house_no', 'N/A')}"
            title += f"\nCity: {data.get('city', 'N/A')}"
        elif ntype == "Vehicle":
            title += f"\nVehicle No: {data.get('reg_no', 'N/A')}"
            title += f"\nModel: {data.get('car_model', 'N/A')}"
            title += f"\nYear: {data.get('model_year', 'N/A')}"
        elif ntype == "Utility":
            title += f"\nUtility: {data.get('utility_type', 'Utility')}"
            title += f"\nConsumer ID: {data.get('consumer_id', 'N/A')}"
            title += f"\nMeter No: {data.get('meter_no', 'N/A')}"
        elif ntype == "Travel":
            title += f"\nTravelling To: {data.get('destination', 'N/A')}"
            title += f"\nPassport No: {data.get('passport_no', 'N/A')}"
            title += f"\nVisa Type: {data.get('visa_type', 'N/A')}"
        elif ntype == "Company":
            title += f"\nCompany Name: {label}"
            title += f"\nCity: {data.get('city', 'N/A')}"
        elif ntype == "Phone":
            title += f"\nPhone Number: {label}"
            title += f"\nAnnual Recharge: {data.get('annual_recharge_amount', 0):,.0f}"
        
        net.add_node(str(node_id), label=label, color=color, size=size, title=title)

    for u, v, data in subgraph.edges(data=True):
        rel = data.get("relationship", "")
        
        # Color-code the new cross-dataset syndicate links so they stand out
        edge_color = "#3a3a5e"
        width = 1
        if rel == "SHARES_FATHER":
            edge_color = "#e74c3c"  # Red
            width = 2
        elif rel == "SHARES_ADDRESS":
            edge_color = "#2ecc71"  # Green
            width = 2
        elif rel == "SHARES_PHONE":
            edge_color = "#f1c40f"  # Yellow
            width = 2
            
        net.add_edge(str(u), str(v), title=rel, label=rel, color=edge_color, width=width)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
        net.save_graph(f.name)
        f.seek(0)
    with open(f.name, "r", encoding="utf-8") as hf:
        html_content = hf.read()
    components.html(html_content, height=height + 20, scrolling=True)


st.markdown("## 🕸️ Knowledge Graph Explorer")
st.markdown('<p style="color:#8888a0;">Interactive visualization of entity relationships and networks</p>',
            unsafe_allow_html=True)

graph_mtime = (MODELS_DIR / "knowledge_graph.pkl").stat().st_mtime if (MODELS_DIR / "knowledge_graph.pkl").exists() else 0
cit_mtime = (PROCESSED_DIR / "master_citizens.csv").stat().st_mtime if (PROCESSED_DIR / "master_citizens.csv").exists() else 0

G = load_graph(graph_mtime)
citizens = load_citizens(cit_mtime)

if G is None:
    st.warning("⚠️ Knowledge graph not built yet. Run the pipeline first.")
    st.stop()

# ── Graph Controls ──────────────────────────────────────────────
with st.expander("⚙️ Graph Controls", expanded=True):
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 2, 1])
    with ctrl_col1:
        view_mode = st.selectbox("View Mode", [
            "Macro View (Communities)",
            "Community Drill-Down",
            "Ego Graph (Person Drill-Down)"
        ])
    
    node_types = list({d.get("node_type", "") for _, d in G.nodes(data=True)})
    with ctrl_col2:
        selected_types = st.multiselect("Node Types", node_types, default=node_types[:5])
    
    with ctrl_col3:
        max_nodes = st.slider("Max Nodes to Render", 20, 1000, 100)
    
    st.markdown("**Optimization & Filtering**")
    opt_col1, opt_col2, opt_col3 = st.columns(3)
    with opt_col1:
        min_degree = st.number_input("Minimum Connections (Edge Filter)", min_value=1, max_value=50, value=1, help="Hide nodes with fewer connections than this.")
    with opt_col2:
        high_risk_only = st.checkbox("🚨 High-Risk Targets Only", value=False, help="Hide compliant or low-risk individuals (Categories A & B)")
    with opt_col3:
        top_centrality_only = st.checkbox("🏆 Top Centrality Focus", value=False, help="Only display the absolute most central individuals.")

# ── Graph Statistics Panel ────────────────────────────────────────
stats_cols = st.columns(4)
with stats_cols[0]:
    st.metric("Total Nodes", f"{G.number_of_nodes():,}")
with stats_cols[1]:
    st.metric("Total Edges", f"{G.number_of_edges():,}")
with stats_cols[2]:
    density = nx.density(G.to_undirected())
    st.metric("Density", f"{density:.4f}")
with stats_cols[3]:
    person_count = sum(1 for _, d in G.nodes(data=True) if d.get("node_type") == "Person")
    st.metric("Person Nodes", f"{person_count:,}")

st.markdown("---")

# ── Graph Filter Function ─────────────────────────────────────────
def apply_graph_filters(graph: nx.Graph) -> nx.Graph:
    nodes_to_keep = []
    
    if top_centrality_only:
        deg_cent = nx.degree_centrality(graph)
        sorted_nodes = sorted(deg_cent.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        central_set = {n for n, _ in sorted_nodes}
    else:
        central_set = set(graph.nodes())

    for n, d in graph.nodes(data=True):
        # Apply centrality filter
        if n not in central_set:
            continue
            
        # Apply min degree filter
        if graph.degree(n) < min_degree:
            # We don't want to accidentally filter out the main target of an ego graph, but we'll apply it strictly here
            continue
            
        # Apply High-Risk filter
        if high_risk_only and d.get("node_type") == "Person":
            cat = str(d.get("risk_category", ""))
            score = float(d.get("risk_score", 0))
            # Hide completely compliant people
            if cat in ["Cat A", "Cat B"] and score < 50:
                continue
                
        nodes_to_keep.append(n)
        
    return graph.subgraph(nodes_to_keep).copy()

# ── View rendering ────────────────────────────────────────────────
if view_mode == "Ego Graph (Person Drill-Down)":
    if citizens is not None and len(citizens) > 0:
        search_q = st.text_input("🔍 Search Citizen by Name or CNIC (English/Urdu):", "")
        
        try:
            from core.entity_resolution.intelligent_search import advanced_fuzzy_search
            if search_q:
                filtered_citizens = advanced_fuzzy_search(citizens, search_q, search_columns=["canonical_name", "cnic"], limit=50)
            else:
                filtered_citizens = citizens.head(50)
        except Exception as e:
            st.error(f"Search failed: {e}")
            filtered_citizens = citizens.head(50)
            
        citizen_options = filtered_citizens["canonical_name"].astype(str) + " (" + filtered_citizens["citizen_id"].astype(str) + ")"
        valid_options = [str(opt) for opt in citizen_options.tolist() if not str(opt).startswith("nan ")]
        
        selected = st.selectbox("Select Citizen", valid_options)
        if selected:
            cid = selected.split("(")[-1].rstrip(")")
            if cid in G:
                radius = st.radio("Depth", [1, 2], horizontal=True)
                ego = nx.ego_graph(G, cid, radius=radius, undirected=True)
                # Filter by selected types
                nodes_to_keep = [n for n in ego.nodes()
                                 if ego.nodes[n].get("node_type", "") in selected_types
                                 or n == cid]
                ego_filtered = ego.subgraph(nodes_to_keep)
                ego_filtered = apply_graph_filters(ego_filtered)
                
                if ego_filtered.number_of_nodes() == 0:
                    st.warning("All nodes filtered out by your current Optimizations & Filtering settings.")
                else:
                    st.markdown(f"**Showing {ego_filtered.number_of_nodes()} nodes, "
                               f"{ego_filtered.number_of_edges()} edges**")
                    render_pyvis_graph(ego_filtered)
            else:
                st.warning("Citizen not found in graph")
    else:
        st.info("No citizen data loaded")

elif view_mode == "Community Drill-Down":
    try:
        from networkx.algorithms.community import louvain_communities
        focus = st.selectbox("Community Filter", [
            "All Relationships",
            "Company & Business Based",
            "City & Property Based",
            "Financial & Banking Based"
        ], help="Filter the network to only look for communities based on specific types of shared assets.")

        with st.spinner("Detecting communities..."):
            undirected = G.to_undirected()
            
            if focus == "Company & Business Based":
                valid_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in ["Person", "Company"]]
                filtered_graph = undirected.subgraph(valid_nodes)
            elif focus == "City & Property Based":
                valid_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in ["Person", "City", "Property", "Address"]]
                filtered_graph = undirected.subgraph(valid_nodes)
            elif focus == "Financial & Banking Based":
                valid_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in ["Person", "Bank", "BankAccount"]]
                filtered_graph = undirected.subgraph(valid_nodes)
            else:
                filtered_graph = undirected

            communities = louvain_communities(filtered_graph, resolution=1.0, seed=42)
            # Filter out singletons (people with no connections in this view)
            communities = sorted([c for c in communities if len(c) > 1], key=len, reverse=True)

        st.markdown(f"**Detected {len(communities)} active communities**")
        
        def get_comm_label(i):
            comm_nodes = communities[i]
            # Analyze what nodes form the basis of this community
            asset_counts = {}
            for n in comm_nodes:
                ntype = G.nodes[n].get("node_type", "Unknown")
                if ntype != "Person":
                    asset_counts[ntype] = asset_counts.get(ntype, 0) + 1
            
            top_assets = sorted(asset_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            basis_parts = []
            for ntype, count in top_assets:
                if ntype.endswith('y'):
                    basis_parts.append(f"{count} {ntype[:-1]}ies")
                else:
                    basis_parts.append(f"{count} {ntype}s")
            
            basis_str = ", ".join(basis_parts) if basis_parts else "Direct links"
            person_count = sum(1 for n in comm_nodes if G.nodes[n].get("node_type") == "Person")
            
            comm_name = get_logical_community_name(G, comm_nodes, focus=focus)
            
            return f"{comm_name} ({person_count} persons) [{basis_str}]"

        options = ["None"] + list(range(min(20, len(communities))))
        comm_idx = st.selectbox("Select Community", options,
                               format_func=lambda i: "--- Select a Community to Render ---" if i == "None" else get_comm_label(i))
        
        if comm_idx != "None" and comm_idx is not None:
            comm_nodes = communities[comm_idx]
            subgraph = G.subgraph(comm_nodes)
            subgraph = apply_graph_filters(subgraph)
            
            # Limit size
            if subgraph.number_of_nodes() > max_nodes:
                nodes = list(subgraph.nodes())[:max_nodes]
                subgraph = subgraph.subgraph(nodes)
                
            if subgraph.number_of_nodes() == 0:
                st.warning("All nodes filtered out by your current Optimizations & Filtering settings.")
            else:
                render_pyvis_graph(subgraph)

            # Members table
            members = [{"ID": n, "Name": G.nodes[n].get("label", ""),
                        "Type": G.nodes[n].get("node_type", "")}
                       for n in subgraph.nodes() if G.nodes[n].get("node_type") == "Person"]
            if members:
                st.markdown(f"#### Community Members ({len(members)} persons)")
                st.dataframe(pd.DataFrame(members).head(50), hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"Community detection failed: {e}")

elif view_mode == "Macro View (Communities)":
    with st.spinner("Clustering communities for Macro View..."):
        from networkx.algorithms.community import louvain_communities
        undirected = G.to_undirected()
        communities = louvain_communities(undirected, resolution=1.0, seed=42)
        communities = sorted([c for c in communities if len(c) > 1], key=len, reverse=True)
        
        # We only want to show the top N communities up to max_nodes
        top_communities = communities[:max_nodes]
        
        macro_graph = nx.Graph()
        node_to_comm = {}
        for i, comm in enumerate(top_communities):
            comm_id = get_logical_community_name(G, comm, focus=None)
            
            # Analyze basis
            asset_counts = {}
            for n in comm:
                ntype = G.nodes[n].get("node_type", "Unknown")
                if ntype != "Person":
                    asset_counts[ntype] = asset_counts.get(ntype, 0) + 1
            top_assets = sorted(asset_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            basis_str = ", ".join([f"{c} {t}" for t, c in top_assets])
            
            person_count = sum(1 for n in comm if G.nodes[n].get("node_type") == "Person")
            
            macro_graph.add_node(comm_id, 
                                 label=f"{comm_id}\n({person_count} People)", 
                                 title=f"Total Members: {len(comm)}\nBasis: {basis_str}",
                                 node_type="Community",
                                 color="#8A2BE2", # Purple
                                 size=min(50, 10 + len(comm))) # Scale by size
            
            for n in comm:
                node_to_comm[n] = comm_id
                
        # Add edges between communities
        for u, v in undirected.edges():
            cu = node_to_comm.get(u)
            cv = node_to_comm.get(v)
            if cu and cv and cu != cv:
                if macro_graph.has_edge(cu, cv):
                    macro_graph[cu][cv]['weight'] += 1
                else:
                    macro_graph.add_edge(cu, cv, weight=1)
                    
        # Apply min_degree edge filter on macro graph
        nodes_to_keep = [n for n in macro_graph.nodes() if macro_graph.degree(n) >= min_degree]
        macro_filtered = macro_graph.subgraph(nodes_to_keep).copy()
        
        if macro_filtered.number_of_nodes() == 0:
            st.warning("All communities filtered out. Try lowering the Minimum Connections filter.")
        else:
            st.markdown(f"**Showing Macro View: {macro_filtered.number_of_nodes()} Community Clusters, "
                       f"{macro_filtered.number_of_edges()} Inter-Community Connections**")
            render_pyvis_graph(macro_filtered)

# ── Centrality Leaderboard ────────────────────────────────────────
st.markdown("---")
st.markdown("#### 🏆 Centrality Leaderboard")

with st.spinner("Computing centrality..."):
    undirected = G.to_undirected()
    degree = nx.degree_centrality(undirected)
    # Get top 20 persons by degree
    person_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "Person"]
    person_degree = {n: degree.get(n, 0) for n in person_nodes}
    top_20 = sorted(person_degree.items(), key=lambda x: x[1], reverse=True)[:20]

    if top_20:
        leader_data = []
        for n, score in top_20:
            counts = {}
            for neighbor in G.neighbors(n):
                ntype = G.nodes[neighbor].get("node_type", "Unknown")
                if ntype == "Person":
                    # For person-to-person connections (via shared address/company), we might just say "Person"
                    pass
                counts[ntype] = counts.get(ntype, 0) + 1
            
            basis_parts = []
            for ntype, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
                if count == 1:
                    basis_parts.append(f"1 {ntype}")
                else:
                    if ntype.endswith('y'):
                        basis_parts.append(f"{count} {ntype[:-1]}ies")
                    else:
                        basis_parts.append(f"{count} {ntype}s")
            
            leader_data.append({
                "Name": G.nodes[n].get("label", n),
                "Degree Centrality": round(score, 4),
                "Total Connections": G.degree(n),
                "Basis of Centrality": ", ".join(basis_parts)
            })
        
        leader_df = pd.DataFrame(leader_data)
        st.dataframe(leader_df, hide_index=True, use_container_width=True)
