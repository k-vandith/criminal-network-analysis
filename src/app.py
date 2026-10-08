"""Streamlit dashboard for Criminal Network Analysis."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from src.graph_engine import CriminalNetworkGraph

st.set_page_config(page_title="Criminal Network Analysis", page_icon="🕸️", layout="wide")
st.title("🕸️ AI-Powered Criminal Network Analysis System")
st.caption("Synthetic data only • Graph intelligence • Centrality • Community detection • Risk scoring")

DATA = ROOT / "data" / "sample" / "synthetic_network.json"


@st.cache_resource
def load_graph() -> CriminalNetworkGraph:
    g = CriminalNetworkGraph()
    if DATA.exists():
        g.import_json(DATA)
        g.compute_risk_scores()
    return g


if not DATA.exists():
    st.warning("Demo data not found. Run: `python scripts/generate_demo_data.py`")
    st.stop()

g = load_graph()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Graph", "Centrality", "Risk Scores", "Suspicious Links", "Search / Timeline"]
)

with tab1:
    st.plotly_chart(g.to_plotly_figure(), use_container_width=True)
    st.metric("Nodes", g.G.number_of_nodes())
    st.metric("Edges", g.G.number_of_edges())

with tab2:
    st.dataframe(g.centrality_analysis(), use_container_width=True)

with tab3:
    risk_df = g.compute_risk_scores()
    st.dataframe(risk_df, use_container_width=True)
    st.bar_chart(risk_df.set_index("name")["risk_score"])

with tab4:
    flags = g.suspicious_relationships()
    st.dataframe(pd.DataFrame(flags), use_container_width=True)

with tab5:
    q = st.text_input("Search entities")
    if q:
        hits = g.search_entities(q)
        st.write([{"id": h.id, "name": h.name, "type": h.entity_type, "risk": h.risk_score} for h in hits])
    st.subheader("Event Timeline")
    st.dataframe(g.timeline_events(), use_container_width=True)
