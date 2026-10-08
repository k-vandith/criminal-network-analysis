from __future__ import annotations

from pathlib import Path

from src.graph_engine import CriminalNetworkGraph, Entity, Relationship
import src.graph_features  # noqa: F401


def build_graph() -> CriminalNetworkGraph:
    g = CriminalNetworkGraph()
    for e in [
        Entity("A", "Alice", "person", {"watchlist": True}),
        Entity("B", "Bob", "person"),
        Entity("C", "Corp", "organization"),
        Entity("D", "Dave", "person"),
    ]:
        g.add_entity(e)
    for r in [
        Relationship("A", "B", "knows", 2.0),
        Relationship("A", "C", "controls", 3.0),
        Relationship("B", "C", "works_for", 1.0),
        Relationship("C", "D", "linked", 2.0),
    ]:
        g.add_relationship(r)
    g.compute_risk_scores()
    return g


def test_key_player_ranking_has_betweenness():
    g = build_graph()
    df = g.key_player_ranking(5)
    assert not df.empty
    assert "betweenness_centrality" in df.columns
    assert "degree_centrality" in df.columns
    assert "kingpin_score" in df.columns
    assert "community" in df.columns
    # Betweenness must be a real centrality value, not a fabricated constant.
    assert df["betweenness_centrality"].notna().all()
    assert df["betweenness_centrality"].max() > 0


def test_bridge_entities():
    df = build_graph().bridge_entities(5)
    assert not df.empty
    assert "cross_community_links" in df.columns


def test_entity_profile():
    profile = build_graph().entity_profile("A")
    assert profile is not None
    assert profile["name"] == "Alice"
    assert "centrality" in profile
    assert "betweenness_centrality" in profile["centrality"]
    assert "neighbors" in profile
    assert "reasons" in profile
    assert "attributes" in profile
    assert profile["attributes"].get("watchlist") is True


def test_shortest_path():
    df = build_graph().shortest_investigation_path("A", "D")
    assert not df.empty
    assert df.iloc[0]["id"] == "A"
    assert df.iloc[-1]["id"] == "D"


def test_shortest_path_missing_node():
    df = build_graph().shortest_investigation_path("A", "MISSING")
    assert df.empty


def test_anomaly_detection():
    df = build_graph().anomaly_detection(5)
    assert not df.empty
    assert "anomaly_score" in df.columns


def test_community_summary():
    df = build_graph().community_summary()
    assert not df.empty
    assert "community" in df.columns


def test_explanations_and_reports(tmp_path: Path):
    g = build_graph()
    explained = g.key_player_explanations(3)
    assert "why_flagged" in explained.columns
    html = g.export_html_report(tmp_path / "report.html")
    assert html.exists()
    assert "not" in html.read_text(encoding="utf-8").lower()
    pdf = g.export_pdf_report(tmp_path / "report.pdf")
    assert pdf.exists()
    assert pdf.suffix.lower() in {".pdf", ".html"}
