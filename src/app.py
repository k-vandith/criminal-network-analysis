"""Professional investigator console for the Criminal Network Analysis system."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph_engine import CriminalNetworkGraph
import src.graph_features  # noqa: F401  # activates advanced features

st.set_page_config(
    page_title="CRIMENET // Intelligence Console",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root { --bg:#080d19; --panel:#11192b; --panel2:#0d1526; --line:#253452; --muted:#91a0ba; --text:#eef4ff; --accent:#55d6ff; --danger:#ff6b7a; --warn:#ffc857; --ok:#58e0a7; }
.stApp { background: radial-gradient(circle at top right, rgba(55,130,180,.10), transparent 30%), var(--bg); color:var(--text); }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1600px; }
section[data-testid="stSidebar"] { background: #09101e; border-right:1px solid var(--line); }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color:var(--text); }
.hero { border:1px solid var(--line); background:linear-gradient(135deg, rgba(18,31,53,.98), rgba(10,18,32,.98)); border-radius:18px; padding:22px 26px; margin-bottom:18px; box-shadow:0 15px 40px rgba(0,0,0,.18); }
.hero-kicker { color:var(--accent); font-size:.78rem; letter-spacing:.18em; font-weight:800; }
.hero-title { font-size:2rem; font-weight:800; margin:.25rem 0; }
.hero-sub { color:var(--muted); font-size:.92rem; }
.metric { border:1px solid var(--line); background:linear-gradient(180deg, rgba(18,27,47,.96), rgba(12,20,35,.96)); border-radius:14px; padding:16px; min-height:100px; }
.metric-label { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { color:var(--text); font-size:1.8rem; font-weight:800; margin-top:.25rem; }
.metric-foot { color:#73839d; font-size:.74rem; }
.section { color:var(--text); font-size:1.12rem; font-weight:800; margin: 1rem 0 .55rem; }
.pill { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 9px; margin-right:6px; color:#b8c7de; font-size:.72rem; }
.signal { border-left:3px solid var(--accent); background:var(--panel2); border-top:1px solid var(--line); border-right:1px solid var(--line); border-bottom:1px solid var(--line); border-radius:10px; padding:11px 13px; margin-bottom:8px; }
.warning { border-left-color:var(--warn); } .danger { border-left-color:var(--danger); }
.small { color:var(--muted); font-size:.78rem; }
div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
button[kind="primary"] { border-radius:10px; }
</style>
""",
    unsafe_allow_html=True,
)

DATA = ROOT / "data" / "sample" / "synthetic_network.json"


@st.cache_resource
def load_graph() -> CriminalNetworkGraph:
    g = CriminalNetworkGraph()
    if DATA.exists():
        g.import_json(DATA)
        g.compute_risk_scores()
    return g


def metric_card(label: str, value: str, foot: str = "") -> None:
    st.markdown(
        f"<div class='metric'><div class='metric-label'>{label}</div>"
        f"<div class='metric-value'>{value}</div><div class='metric-foot'>{foot}</div></div>",
        unsafe_allow_html=True,
    )


def risk_badge(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.50:
        return "ELEVATED"
    if score >= 0.25:
        return "MODERATE"
    return "LOW"


def entity_options(graph: CriminalNetworkGraph, node_ids: list[str] | None = None) -> list[str]:
    ids = node_ids if node_ids is not None else list(graph.G.nodes)
    return [
        f"{graph.entities[n].name if n in graph.entities else n} · {n}"
        for n in ids
    ]


def id_from_option(option: str) -> str:
    return option.rsplit(" · ", 1)[-1]


def graph_figure(graph: CriminalNetworkGraph, visible_nodes: list[str]) -> go.Figure:
    if not visible_nodes:
        return go.Figure()
    sub = graph.G.subgraph(visible_nodes).copy()
    if sub.number_of_nodes() == 0:
        return go.Figure()

    import networkx as nx

    pos = nx.spring_layout(sub, seed=42, weight="weight")
    edge_x, edge_y = [], []
    for u, v in sub.edges:
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#2f405f"),
        hoverinfo="none",
    )

    node_x, node_y, labels, colors, sizes, custom = [], [], [], [], [], []
    for nid in sub.nodes:
        ent = graph.entities.get(nid)
        risk = float(ent.risk_score if ent else sub.nodes[nid].get("risk_score", 0.0))
        name = ent.name if ent else str(nid)
        kind = ent.entity_type if ent else sub.nodes[nid].get("entity_type", "unknown")
        degree = graph.G.degree(nid)
        node_x.append(pos[nid][0])
        node_y.append(pos[nid][1])
        labels.append(
            f"<b>{name}</b><br>{kind}<br>Analytical risk {risk:.2f}<br>{degree} direct links"
        )
        colors.append(risk)
        sizes.append(12 + 34 * risk + min(degree, 12))
        custom.append([nid, name, kind, risk, degree])

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        text=labels,
        hoverinfo="text",
        customdata=custom,
        marker=dict(
            size=sizes,
            color=colors,
            colorscale="YlOrRd",
            cmin=0,
            cmax=1,
            showscale=True,
            colorbar=dict(title="Analytical risk"),
            line=dict(width=1, color="#d7e5ff"),
            opacity=0.92,
        ),
    )

    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        height=660,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=5, r=5, t=8, b=5),
        showlegend=False,
        hoverlabel=dict(bgcolor="#101a30", font_size=13),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    return fig


if not DATA.exists():
    st.markdown(
        "<div class='hero'><div class='hero-title'>Demo data not found</div>"
        "<div class='hero-sub'>Run <code>python scripts/generate_demo_data.py</code> from the project root.</div></div>",
        unsafe_allow_html=True,
    )
    st.stop()

g = load_graph()
risk = g.compute_risk_scores()
communities = g.community_detection()
community_count = len(set(communities.values()))

with st.sidebar:
    st.markdown("### CRIMENET")
    st.caption("LOCAL INTELLIGENCE CONSOLE")
    st.divider()
    st.markdown("**Graph controls**")
    q = st.text_input("Search", placeholder="name, ID, entity type")
    types = sorted({e.entity_type for e in g.entities.values()})
    selected_types = st.multiselect("Entity types", types, default=types)
    risk_min = st.slider("Minimum analytical risk", 0.0, 1.0, 0.0, 0.05)
    community_choices = sorted(set(communities.values()))
    selected_communities = st.multiselect("Communities", community_choices, default=community_choices)
    st.divider()
    st.markdown("**Mode**")
    st.caption("Synthetic dataset · offline analysis")
    st.caption("Analytical risk is a heuristic, not a finding of guilt or legal evidence.")

filtered = []
for nid, ent in g.entities.items():
    score = float(ent.risk_score)
    name_hit = (
        not q
        or q.lower() in ent.name.lower()
        or q.lower() in nid.lower()
        or q.lower() in ent.entity_type.lower()
    )
    comm_hit = communities.get(nid, -1) in selected_communities
    type_hit = ent.entity_type in selected_types
    if name_hit and comm_hit and type_hit and score >= risk_min:
        filtered.append(nid)

st.markdown(
    "<div class='hero'><div class='hero-kicker'>NETWORK INTELLIGENCE // OFFLINE</div>"
    "<div class='hero-title'>Criminal Network Analysis Console</div>"
    "<div class='hero-sub'>Explore entities, communities, bridge candidates, anomaly candidates, "
    "paths, and explainable analytical priority. Scores are review aids, not proof.</div></div>",
    unsafe_allow_html=True,
)

high_risk = int((risk["risk_score"] >= 0.75).sum()) if not risk.empty else 0
avg_risk = float(risk["risk_score"].mean()) if not risk.empty else 0.0

m = st.columns(5)
with m[0]:
    metric_card("Entities", f"{g.G.number_of_nodes():,}", f"{len(filtered):,} visible")
with m[1]:
    metric_card("Relationships", f"{g.G.number_of_edges():,}", "weighted undirected")
with m[2]:
    metric_card("Communities", f"{community_count:,}", "detected clusters")
with m[3]:
    metric_card("High analytical risk", f"{high_risk:,}", "risk ≥ 0.75")
with m[4]:
    metric_card("Avg. analytical risk", f"{avg_risk:.2f}", risk_badge(avg_risk))

tab_overview, tab_network, tab_investigate, tab_signals, tab_entities, tab_timeline, tab_reports = st.tabs(
    ["Overview", "Network", "Investigate", "Signals", "Entities", "Timeline", "Reports"]
)

with tab_overview:
    left, right = st.columns([1.75, 1])
    with left:
        st.markdown("<div class='section'>Network overview</div>", unsafe_allow_html=True)
        st.plotly_chart(graph_figure(g, filtered), use_container_width=True, config={"displaylogo": False})
    with right:
        st.markdown("<div class='section'>Priority queue</div>", unsafe_allow_html=True)
        queue = g.key_player_explanations(8)
        for _, row in queue.head(6).iterrows():
            tone = "danger" if row["risk_score"] >= 0.75 else "warning"
            st.markdown(
                f"<div class='signal {tone}'>"
                f"<b>{int(row['rank']):02d} · {row['name']}</b><br>"
                f"<span class='small'>{row['entity_type']} · analytical priority {row['kingpin_score']:.2f} "
                f"· analytical risk {row['risk_score']:.2f}</span><br>"
                f"<span class='small'>Signal for review: {row['why_flagged']}</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div class='section'>Network signals</div>", unsafe_allow_html=True)
        bridges = g.bridge_entities(5)
        anomalies = g.anomaly_detection(5)
        st.write(f"**{len(bridges)}** bridge candidates · **{len(anomalies)}** anomaly candidates")
        st.caption("Signals are ranked for analyst review; they are not conclusions.")

with tab_network:
    st.markdown("<div class='section'>Filtered network workspace</div>", unsafe_allow_html=True)
    st.caption(f"Showing {len(filtered)} of {g.G.number_of_nodes()} entities. Adjust filters in the sidebar.")
    st.plotly_chart(graph_figure(g, filtered), use_container_width=True, config={"displaylogo": False})
    with st.expander("Interactive physics graph"):
        html = g.to_pyvis_html(ROOT / "data" / "sample" / "network_interactive.html")
        components.html(html, height=640, scrolling=True)

with tab_investigate:
    options = entity_options(g, filtered or list(g.G.nodes))
    if not options:
        st.info("No entities match the current filters.")
    else:
        col_a, col_b = st.columns([1, 1])
        with col_a:
            selected = st.selectbox("Entity", options, key="inspect_entity")
            eid = id_from_option(selected)
            profile = g.entity_profile(eid)
            if profile:
                st.markdown(f"### {profile['name']}")
                st.write(f"`{profile['id']}` · {profile['entity_type']} · Community {profile['community']}")
                st.metric("Analytical risk", f"{profile['risk_score']:.2f}", risk_badge(profile["risk_score"]))
                st.markdown("**Why it is surfaced**")
                if profile["reasons"]:
                    for reason in profile["reasons"]:
                        st.write(f"• {reason}")
                else:
                    st.caption("No special explanation signal triggered.")
                st.markdown("**Attributes supplied in source data**")
                st.json(profile["attributes"] or {"status": "none"})
        with col_b:
            st.markdown("### Centrality")
            if profile:
                c = profile["centrality"]
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"metric": "Degree", "value": c.get("degree_centrality", 0)},
                            {"metric": "Betweenness", "value": c.get("betweenness_centrality", 0)},
                            {"metric": "Closeness", "value": c.get("closeness_centrality", 0)},
                            {"metric": "Eigenvector", "value": c.get("eigenvector_centrality", 0)},
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
                st.markdown("### Direct relationships")
                st.dataframe(pd.DataFrame(profile["neighbors"]), hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("### Relationship path")
        source = st.selectbox("From", options, key="path_source")
        target = st.selectbox("To", options, index=min(1, len(options) - 1), key="path_target")
        sid, tid = id_from_option(source), id_from_option(target)
        if sid == tid:
            st.info("Choose two different entities to calculate a path.")
        else:
            path_df = g.shortest_investigation_path(sid, tid)
            if path_df.empty:
                st.warning("No path found between these entities.")
            else:
                st.success(f"Shortest relationship path: {len(path_df) - 1} hop(s)")
                st.dataframe(path_df, hide_index=True, use_container_width=True)

with tab_signals:
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("<div class='section'>Bridge candidates</div>", unsafe_allow_html=True)
        st.dataframe(g.bridge_entities(20), hide_index=True, use_container_width=True)
    with s2:
        st.markdown("<div class='section'>Anomaly candidates</div>", unsafe_allow_html=True)
        st.dataframe(g.anomaly_detection(20), hide_index=True, use_container_width=True)

    st.markdown("<div class='section'>Suspicious relationships</div>", unsafe_allow_html=True)
    st.caption("Signal for review. High weight or cross-community links are heuristics.")
    flags = pd.DataFrame(g.suspicious_relationships())
    st.dataframe(flags, hide_index=True, use_container_width=True)

    st.markdown("<div class='section'>Potential links</div>", unsafe_allow_html=True)
    st.dataframe(g.link_prediction(20), hide_index=True, use_container_width=True)

with tab_entities:
    rank = g.key_player_explanations(25)
    st.markdown("<div class='section'>Analytical priority ranking</div>", unsafe_allow_html=True)
    st.caption("Composite of analytical risk, betweenness, degree, and eigenvector centrality. Not a finding of guilt.")
    st.dataframe(rank, hide_index=True, use_container_width=True)

    st.markdown("<div class='section'>Community profiles</div>", unsafe_allow_html=True)
    st.dataframe(g.community_summary(), hide_index=True, use_container_width=True)

    st.markdown("<div class='section'>Full centrality table</div>", unsafe_allow_html=True)
    st.dataframe(g.centrality_analysis(), hide_index=True, use_container_width=True)

with tab_timeline:
    st.markdown("<div class='section'>Event timeline</div>", unsafe_allow_html=True)
    timeline = g.timeline_events()
    if timeline.empty:
        st.info("No event entities are present in the current dataset.")
    else:
        st.dataframe(timeline, hide_index=True, use_container_width=True)
        if "date" in timeline.columns:
            counts = timeline.copy()
            counts["date"] = pd.to_datetime(counts["date"], errors="coerce")
            counts = (
                counts.dropna(subset=["date"])
                .assign(month=lambda x: x["date"].dt.to_period("M").astype(str))
                .groupby("month")
                .size()
                .reset_index(name="events")
            )
            if not counts.empty:
                st.bar_chart(counts.set_index("month"), use_container_width=True)

with tab_reports:
    st.markdown("<div class='section'>Investigation deliverables</div>", unsafe_allow_html=True)
    st.caption("Reports are generated locally from the current synthetic graph.")
    out_dir = ROOT / "data" / "sample"
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate HTML report", use_container_width=True):
            p = g.export_html_report(out_dir / "network_intelligence_report.html")
            st.download_button(
                "Download HTML",
                p.read_text(encoding="utf-8"),
                file_name=p.name,
                use_container_width=True,
            )
    with c2:
        if st.button("Generate PDF report", use_container_width=True):
            p = g.export_pdf_report(out_dir / "network_intelligence_report.pdf")
            if p.suffix.lower() == ".pdf":
                st.download_button(
                    "Download PDF",
                    p.read_bytes(),
                    file_name=p.name,
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.warning(f"PDF dependency unavailable; HTML fallback created at {p}")

    st.markdown("### Data handling")
    st.info(
        "Core analysis is local. Keep real case data out of a public repository. "
        "The included demo dataset is synthetic. Treat analytical priority as a review aid, not evidence."
    )

st.markdown(
    "<div class='small' style='margin-top:18px'>CRIMENET · local graph intelligence · synthetic demo mode · "
    "heuristic scores are not legal evidence</div>",
    unsafe_allow_html=True,
)
