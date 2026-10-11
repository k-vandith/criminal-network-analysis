from __future__ import annotations

import networkx as nx
import pandas as pd

from linklens.core import (
    GraphBundle,
    analyze,
    build_from_interactions,
    build_from_nodes_edges,
    sample_case,
    suspicious_findings,
    timeline_frame,
)


def test_duplicate_edges_preserve_each_valid_interaction_date():
    frame = pd.DataFrame({
        "source": ["A", "A", "B", "B"],
        "target": ["B", "B", "C", "B"],
        "date": ["2025-01-01", "2025-01-02", "2025-01-02", "2025-01-03"],
    })
    bundle = build_from_interactions(frame, "source", "target", date_col="date")

    assert bundle.graph.number_of_edges() == 2
    assert bundle.graph["A"]["B"]["interaction_count"] == 2
    timeline = timeline_frame(bundle).set_index("Date")["Interactions"].to_dict()
    assert timeline == {"2025-01-01": 1, "2025-01-02": 2}
    assert any("self-links" in warning for warning in bundle.warnings)
    assert not bundle.graph.has_edge("B", "B")


def test_sample_timeline_counts_events_not_aggregated_edges():
    bundle = sample_case()
    timeline = timeline_frame(bundle)
    assert int(timeline["Interactions"].sum()) == bundle.graph.graph["interaction_rows"]


def test_invalid_nonempty_dates_are_reported_and_omitted_from_timeline():
    frame = pd.DataFrame({
        "source": ["A", "A", "B"],
        "target": ["B", "B", "C"],
        "date": ["not-a-date", "2025-01-02", "also-not-a-date"],
    })
    bundle = build_from_interactions(frame, "source", "target", date_col="date")

    assert any("2 invalid non-empty date" in warning for warning in bundle.warnings)
    timeline = timeline_frame(bundle).set_index("Date")["Interactions"].to_dict()
    assert timeline == {"2025-01-02": 1}


def test_nodes_and_edges_import_warns_on_invalid_dates_and_skips_self_links():
    nodes = pd.DataFrame([{"id": "A", "type": "person"}, {"id": "B", "type": "person"}])
    edges = pd.DataFrame({
        "source": ["A", "A", "B"],
        "target": ["B", "B", "B"],
        "date": ["bad-date", "2025-03-01", "2025-03-02"],
    })
    bundle = build_from_nodes_edges(
        nodes, edges, "id", "source", "target", node_type_col="type", date_col="date"
    )

    assert not bundle.graph.has_edge("B", "B")
    assert any("self-links" in warning for warning in bundle.warnings)
    assert any("1 invalid non-empty date" in warning for warning in bundle.warnings)
    timeline = timeline_frame(bundle).set_index("Date")["Interactions"].to_dict()
    assert timeline == {"2025-03-01": 1}


def test_random_er_null_graphs_do_not_all_raise_bridge_findings():
    findings_graphs = 0
    graph_count = 60
    for seed in range(graph_count):
        graph = nx.erdos_renyi_graph(40, 0.08, seed=seed)
        nx.set_node_attributes(graph, {node: f"N{node}" for node in graph}, "name")
        nx.set_node_attributes(graph, "person", "entity_type")
        bundle = GraphBundle(graph, source_label=f"ER null seed {seed}")
        if suspicious_findings(bundle, analyze(bundle)):
            findings_graphs += 1

    # Fixed-seed sanity guard for this null model; not a universal production FPR guarantee.
    assert findings_graphs <= 9, f"{findings_graphs}/{graph_count} null graphs raised a finding"


def test_planted_single_person_bridge_is_still_reported():
    graph = nx.Graph()
    left = [f"L{i}" for i in range(10)]
    right = [f"R{i}" for i in range(10)]
    graph.add_edges_from((a, b) for i, a in enumerate(left) for b in left[i + 1:])
    graph.add_edges_from((a, b) for i, a in enumerate(right) for b in right[i + 1:])
    graph.add_edges_from([(left[0], "BRIDGE-PERSON"), ("BRIDGE-PERSON", right[0])])
    nx.set_node_attributes(graph, {node: node for node in graph}, "name")
    nx.set_node_attributes(graph, "person", "entity_type")

    findings = suspicious_findings(GraphBundle(graph), analyze(GraphBundle(graph)))
    assert any(finding["entity_id"] == "BRIDGE-PERSON" for finding in findings)
