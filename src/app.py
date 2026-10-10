"""CRIMENET network intelligence workspace."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph_engine import CriminalNetworkGraph
import src.graph_features  # noqa: F401
from src.services.case_store import CaseStore
from src.ui.theme import THEME_CSS
from src.ui.workspace import render

st.set_page_config(
    page_title="CRIMENET",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(THEME_CSS, unsafe_allow_html=True)

DATA = ROOT / "data" / "sample" / "synthetic_network.json"
CASES = ROOT / "data" / "cases" / "cases.json"


@st.cache_resource
def load_graph() -> CriminalNetworkGraph:
    g = CriminalNetworkGraph()
    if DATA.exists():
        g.import_json(DATA)
        g.compute_risk_scores()
    return g


if not DATA.exists():
    st.markdown(
        "<div class='panel'><div class='h'>Demo data not found</div>"
        "<div class='muted'>Run python scripts/generate_demo_data.py from the project root.</div></div>",
        unsafe_allow_html=True,
    )
    st.stop()

render(load_graph(), CaseStore(CASES), DATA.parent)
