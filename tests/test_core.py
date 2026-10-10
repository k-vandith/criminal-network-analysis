from __future__ import annotations

import pandas as pd
import pytest

from linklens.core import (
    analyze, build_from_interactions, build_from_nodes_edges, graph_stats,
    likely_hidden_links, sample_case, suspicious_findings, timeline_frame,
)
from linklens.io import bundle_from_json, template_csv


def test_sample_case_is_fictional_and_nontrivial():
    bundle = sample_case()
    stats = graph_stats(bundle)
    assert stats["entities"] == 51
    assert stats["relationships"] > 50
    assert all(attrs.get("fictional") for _, attrs in bundle.graph.nodes(data=True))


def test_analysis_returns_ranked_explanations():
    bundle = sample_case()
    result = analyze(bundle)
    assert not result["metrics"].empty
    assert result["metrics"].review_priority.between(0, 100).all()
    assert result["communities"]
    assert isinstance(suspicious_findings(bundle, result), list)


def test_interaction_mapping_and_date_timeline():
    frame = pd.DataFrame({"caller": ["A", "B", "A"], "callee": ["B", "C", "C"],
                          "when": ["2025-01-01", "2025-01-02", "2025-01-03"],
                          "kind": ["call", "payment", "call"]})
    bundle = build_from_interactions(frame, "caller", "callee", "kind", "when")
    assert bundle.graph.number_of_nodes() == 3
    assert bundle.graph.number_of_edges() == 3
    assert len(timeline_frame(bundle)) == 3


def test_interaction_mapping_rejects_bad_columns():
    with pytest.raises(ValueError, match="valid source and target"):
        build_from_interactions(pd.DataFrame({"a": ["x"]}), "missing", "a")


def test_empty_relationships_fail_friendly():
    with pytest.raises(ValueError, match="empty"):
        build_from_interactions(pd.DataFrame(columns=["source", "target"]), "source", "target")


def test_nodes_edges_add_unknown_endpoint_and_metadata():
    nodes = pd.DataFrame([{"id": "A", "name": "Alice", "type": "person"}])
    edges = pd.DataFrame([{"source": "A", "target": "B", "relationship": "calls", "date": "2025-04-03", "weight": 2}])
    bundle = build_from_nodes_edges(nodes, edges, "id", "source", "target", "name", "type", "relationship", "date", "weight")
    assert bundle.graph.nodes["B"]["entity_type"] == "unknown"
    assert bundle.graph["A"]["B"]["weight"] == 2


def test_json_interactions_and_templates():
    bundle = bundle_from_json(b'[{"source":"A","target":"B","date":"2025-01-01"}]', "sample.json")
    assert bundle.graph.has_edge("A", "B")
    assert b"source,target" in template_csv()


def test_hidden_links_table_has_expected_columns():
    frame = pd.DataFrame({"source": ["A", "A", "B", "C"], "target": ["B", "C", "D", "D"]})
    bundle = build_from_interactions(frame, "source", "target")
    assert "Structural confidence" in likely_hidden_links(bundle).columns


def test_no_real_person_claims_in_sample():
    bundle = sample_case()
    assert "Fictional" in bundle.source_label
