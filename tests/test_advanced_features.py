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
    df = build_graph().key_player_ranking(5)
    assert not df.empty
    assert "betweenness_centrality" in df.columns
    assert "betweenness_centrality_x" not in df.columns
    assert "betweenness_centrality_y" not in df.columns
    assert df["betweenness_centrality"].notna().all()


def test_bridge_entities():
    df = build_graph().bridge_entities(5)
    assert not df.empty
    assert "cross_community_links" in df.columns


def test_entity_profile():
    profile = build_graph().entity_profile("A")
    assert profile is not None
    assert profile["name"] == "Alice"
    assert "betweenness_centrality" in profile["centrality"]
    assert profile["attributes"].get("watchlist") is True


def test_shortest_path():
    df = build_graph().shortest_investigation_path("A", "D")
    assert df.iloc[0]["id"] == "A"
    assert df.iloc[-1]["id"] == "D"


def test_shortest_path_missing_node():
    assert build_graph().shortest_investigation_path("A", "MISSING").empty


def test_anomaly_detection():
    df = build_graph().anomaly_detection(5)
    assert "anomaly_score" in df.columns


def test_community_summary():
    assert "community" in build_graph().community_summary().columns


def test_explanations_and_reports(tmp_path: Path):
    g = build_graph()
    assert "why_flagged" in g.key_player_explanations(3).columns
    html = g.export_html_report(tmp_path / "report.html")
    assert "not" in html.read_text(encoding="utf-8").lower()
    pdf = g.export_pdf_report(tmp_path / "report.pdf")
    assert pdf.suffix.lower() in {".pdf", ".html"}


def test_health_and_weighted_path():
    g = build_graph()
    health = g.network_health()
    assert health["entities"] == 4
    path = g.weighted_investigation_path("A", "D")
    assert path.iloc[-1]["id"] == "D"
    assert "A" in g.neighborhood("A", 2)
