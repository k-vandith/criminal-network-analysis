#!/usr/bin/env python3
"""Generate synthetic criminal network data (no real persons)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph_engine import CriminalNetworkGraph, Entity, Relationship

OUT = ROOT / "data" / "sample" / "synthetic_network.json"


def build() -> CriminalNetworkGraph:
    g = CriminalNetworkGraph()
    entities = [
        Entity("P1", "Alex Rivera", "person", {"role": "coordinator", "watchlist": True, "prior_arrests": 2}),
        Entity("P2", "Jordan Lee", "person", {"role": "courier", "prior_arrests": 1}),
        Entity("P3", "Sam Patel", "person", {"role": "financier"}),
        Entity("P4", "Casey Morgan", "person", {"role": "lookout", "suspicious_flag": True}),
        Entity("P5", "Riley Quinn", "person", {"role": "driver"}),
        Entity("O1", "Harbor Logistics LLC", "organization", {"sector": "shipping"}),
        Entity("O2", "Night Owl Holdings", "organization", {"sector": "shell"}),
        Entity("L1", "Dockside Warehouse 12", "location", {"city": "Metro City"}),
        Entity("L2", "Industrial Park Unit 7", "location", {"city": "Metro City"}),
        Entity("A1", "acct-88421", "account", {"bank": "synthetic"}),
        Entity("A2", "acct-33109", "account", {"bank": "synthetic"}),
        Entity("PH1", "+1-555-0101", "phone"),
        Entity("PH2", "+1-555-0199", "phone"),
        Entity("V1", "Truck-XR-442", "vehicle", {"plate": "SYN-442"}),
        Entity("E1", "Shipment Intercept 2025-03", "event", {"date": "2025-03-12", "location": "L1", "description": "Seized cargo"}),
        Entity("E2", "Cash Drop 2025-04", "event", {"date": "2025-04-02", "location": "L2", "description": "Surveillance"}),
    ]
    for e in entities:
        g.add_entity(e)

    rels = [
        Relationship("P1", "P2", "directs", 3.0),
        Relationship("P1", "P3", "finances", 2.5),
        Relationship("P1", "O1", "controls", 2.0),
        Relationship("P2", "P4", "works_with", 1.5),
        Relationship("P2", "V1", "uses", 2.0),
        Relationship("P3", "A1", "owns", 2.5),
        Relationship("P3", "O2", "controls", 3.0),
        Relationship("P4", "PH1", "uses", 1.0),
        Relationship("P5", "V1", "drives", 2.0),
        Relationship("P5", "P2", "associates", 1.5),
        Relationship("O1", "L1", "operates_at", 2.0),
        Relationship("O2", "A2", "owns", 2.0),
        Relationship("P1", "PH2", "uses", 1.5),
        Relationship("P1", "E1", "involved", 2.5),
        Relationship("P2", "E1", "involved", 2.0),
        Relationship("P3", "E2", "involved", 2.0),
        Relationship("P4", "E2", "involved", 1.5),
        Relationship("L1", "E1", "location_of", 1.0),
        Relationship("L2", "E2", "location_of", 1.0),
        Relationship("O1", "O2", "linked", 1.5),
    ]
    for r in rels:
        g.add_relationship(r)
    return g


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    g = build()
    g.compute_risk_scores()
    g.export_json(OUT)
    print(f"Wrote synthetic network → {OUT}")
    print(f"Nodes: {g.G.number_of_nodes()}, Edges: {g.G.number_of_edges()}")


if __name__ == "__main__":
    main()
