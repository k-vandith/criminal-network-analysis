"""Tests for graph engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.graph_engine import CriminalNetworkGraph, Entity, Relationship
import src.graph_features  # noqa: F401


@pytest.fixture
def sample_graph() -> CriminalNetworkGraph:
    g = CriminalNetworkGraph()
    g.add_entity(Entity("A", "Alice", "person", {"watchlist": True}))
    g.add_entity(Entity("B", "Bob", "person"))
    g.add_entity(Entity("C", "Corp", "organization"))
    g.add_relationship(Relationship("A", "B", "knows", 2.0))
    g.add_relationship(Relationship("A", "C", "controls", 3.0))
    g.add_relationship(Relationship("B", "C", "works_for", 1.0))
    return g


def test_add_and_count(sample_graph: CriminalNetworkGraph):
    assert sample_graph.G.number_of_nodes() == 3
    assert sample_graph.G.number_of_edges() == 3


def test_centrality(sample_graph: CriminalNetworkGraph):
    df = sample_graph.centrality_analysis()
    assert not df.empty
    assert "betweenness_centrality" in df.columns


def test_risk(sample_graph: CriminalNetworkGraph):
    df = sample_graph.compute_risk_scores()
    assert df.loc[df["id"] == "A", "risk_score"].values[0] > 0


def test_communities(sample_graph: CriminalNetworkGraph):
    assert len(sample_graph.community_detection()) == 3


def test_search(sample_graph: CriminalNetworkGraph):
    hits = sample_graph.search_entities("alice")
    assert len(hits) == 1 and hits[0].id == "A"


def test_export_import(sample_graph: CriminalNetworkGraph, tmp_path: Path):
    path = tmp_path / "net.json"
    sample_graph.export_json(path)
    g2 = CriminalNetworkGraph()
    g2.import_json(path)
    assert g2.G.number_of_nodes() == 3


def test_suspicious(sample_graph: CriminalNetworkGraph):
    flags = sample_graph.suspicious_relationships(min_weight=2.0)
    assert any(f["weight"] >= 2.0 for f in flags)


def test_link_prediction(sample_graph: CriminalNetworkGraph):
    df = sample_graph.link_prediction(5)
    assert df.empty or "score" in df.columns


def test_key_player_ranking(sample_graph: CriminalNetworkGraph):
    df = sample_graph.key_player_ranking(3)
    assert not df.empty and "kingpin_score" in df.columns
    assert df.iloc[0]["rank"] == 1


def test_html_report(sample_graph: CriminalNetworkGraph, tmp_path: Path):
    p = sample_graph.export_html_report(tmp_path / "r.html")
    assert p.exists() and len(p.read_text(encoding="utf-8")) > 50


def test_pyvis_html(sample_graph: CriminalNetworkGraph, tmp_path: Path):
    html = sample_graph.to_pyvis_html(tmp_path / "g.html")
    assert len(html) > 20
