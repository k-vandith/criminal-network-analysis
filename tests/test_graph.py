"""Tests for graph engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.graph_engine import CriminalNetworkGraph, Entity, Relationship


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
    assert set(df["id"]) == {"A", "B", "C"}


def test_risk(sample_graph: CriminalNetworkGraph):
    df = sample_graph.compute_risk_scores()
    assert df.loc[df["id"] == "A", "risk_score"].values[0] > 0
    assert df["risk_score"].max() <= 1.0


def test_communities(sample_graph: CriminalNetworkGraph):
    mapping = sample_graph.community_detection()
    assert len(mapping) == 3


def test_search(sample_graph: CriminalNetworkGraph):
    hits = sample_graph.search_entities("alice")
    assert len(hits) == 1
    assert hits[0].id == "A"


def test_export_import(sample_graph: CriminalNetworkGraph, tmp_path: Path):
    path = tmp_path / "net.json"
    sample_graph.export_json(path)
    g2 = CriminalNetworkGraph()
    g2.import_json(path)
    assert g2.G.number_of_nodes() == 3
    assert g2.G.number_of_edges() == 3


def test_suspicious(sample_graph: CriminalNetworkGraph):
    flags = sample_graph.suspicious_relationships(min_weight=2.0)
    assert any(f["weight"] >= 2.0 for f in flags)
