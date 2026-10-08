"""Streamlit dashboard for Criminal Network Analysis."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from src.graph_engine import CriminalNetworkGraph

st.set_page_config(page_title="Criminal Network Analysis", page_icon="🕸️", layout="wide")
st.title("🕸️ AI-Powered Criminal Network Analysis System")
st.caption(
    "Synthetic data only · Centrality · Communities · Risk · Link prediction · Kingpins · Reports"
)

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["Graph", "Centrality", "Kingpins", "Link Prediction", "Suspicious Links", "Search / Timeline", "Reports"]
)

with tab1:
    st.plotly_chart(g.to_plotly_figure(), use_container_width=True)
    c1, c2 = st.columns(2)
    c1.metric("Nodes", g.G.number_of_nodes())
    c2.metric("Edges", g.G.number_of_edges())
    with st.expander("Interactive pyvis graph"):
        html_path = ROOT / "data" / "sample" / "network_interactive.html"
        html = g.to_pyvis_html(html_path)
        components.html(html, height=620, scrolling=True)

with tab2:
    st.dataframe(g.centrality_analysis(), use_container_width=True)

with tab3:
    st.subheader("Key player / kingpin ranking")
    st.dataframe(g.key_player_ranking(15), use_container_width=True)

with tab4:
    st.subheader("Predicted missing links")
    st.dataframe(g.link_prediction(15), use_container_width=True)

with tab5:
    flags = g.suspicious_relationships()
    st.dataframe(pd.DataFrame(flags), use_container_width=True)

with tab6:
    q = st.text_input("Search entities")
    if q:
        hits = g.search_entities(q)
        st.write([{"id": h.id, "name": h.name, "type": h.entity_type, "risk": h.risk_score} for h in hits])
    st.subheader("Event Timeline")
    st.dataframe(g.timeline_events(), use_container_width=True)

with tab7:
    st.subheader("Export reports")
    out_dir = ROOT / "data" / "sample"
    if st.button("Generate HTML report"):
        p = g.export_html_report(out_dir / "network_report.html")
        st.success(f"Wrote {p}")
        st.download_button("Download HTML", p.read_text(encoding="utf-8"), file_name="network_report.html")
    if st.button("Generate PDF report"):
        p = g.export_pdf_report(out_dir / "network_report.pdf")
        st.success(f"Wrote {p}")
        if p.suffix == ".pdf":
            st.download_button("Download PDF", p.read_bytes(), file_name=p.name)
        else:
            st.info("PDF engine unavailable; HTML report written instead.")
