"""Graph construction, analysis, and risk scoring for criminal network intelligence."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)

ENTITY_TYPES = ("person", "organization", "location", "account", "phone", "vehicle", "event")


@dataclass
class Entity:
    id: str
    name: str
    entity_type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0


@dataclass
class Relationship:
    source: str
    target: str
    rel_type: str
    weight: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)


class CriminalNetworkGraph:
    """In-memory graph intelligence engine using NetworkX."""

    def __init__(self) -> None:
        self.G = nx.Graph()
        self.entities: dict[str, Entity] = {}

    def add_entity(self, entity: Entity) -> None:
        if entity.entity_type not in ENTITY_TYPES:
            raise ValueError(f"Unknown entity type: {entity.entity_type}")
        self.entities[entity.id] = entity
        self.G.add_node(
            entity.id,
            name=entity.name,
            entity_type=entity.entity_type,
            risk_score=entity.risk_score,
            **entity.attributes,
        )

    def add_relationship(self, rel: Relationship) -> None:
        if rel.source not in self.G or rel.target not in self.G:
            raise ValueError("Both endpoints must exist before adding a relationship")
        self.G.add_edge(
            rel.source,
            rel.target,
            rel_type=rel.rel_type,
            weight=rel.weight,
            **rel.attributes,
        )

    def centrality_analysis(self) -> pd.DataFrame:
        if self.G.number_of_nodes() == 0:
            return pd.DataFrame()
        degree = nx.degree_centrality(self.G)
        betweenness = nx.betweenness_centrality(self.G, weight="weight")
        closeness = nx.closeness_centrality(self.G)
        try:
            eigenvector = nx.eigenvector_centrality(self.G, max_iter=500, weight="weight")
        except nx.PowerIterationFailedConvergence:
            eigenvector = {n: 0.0 for n in self.G.nodes}
        rows = []
        for nid in self.G.nodes:
            ent = self.entities.get(nid)
            rows.append(
                {
                    "id": nid,
                    "name": ent.name if ent else nid,
                    "entity_type": ent.entity_type if ent else "unknown",
                    "degree_centrality": round(degree.get(nid, 0), 4),
                    "betweenness_centrality": round(betweenness.get(nid, 0), 4),
                    "closeness_centrality": round(closeness.get(nid, 0), 4),
                    "eigenvector_centrality": round(eigenvector.get(nid, 0), 4),
                }
            )
        return pd.DataFrame(rows).sort_values("betweenness_centrality", ascending=False)

    def community_detection(self) -> dict[str, int]:
        if self.G.number_of_nodes() == 0:
            return {}
        try:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = list(greedy_modularity_communities(self.G, weight="weight"))
        except Exception:
            communities = list(nx.connected_components(self.G))
        mapping: dict[str, int] = {}
        for i, comm in enumerate(communities):
            for node in comm:
                mapping[node] = i
        return mapping

    def compute_risk_scores(self) -> pd.DataFrame:
        """Heuristic risk scoring based on centrality + suspicious attributes."""
        cent = self.centrality_analysis()
        if cent.empty:
            return cent
        communities = self.community_detection()
        scores = []
        for _, row in cent.iterrows():
            base = (
                0.35 * row["betweenness_centrality"]
                + 0.25 * row["degree_centrality"]
                + 0.20 * row["eigenvector_centrality"]
                + 0.20 * row["closeness_centrality"]
            )
            ent = self.entities.get(row["id"])
            bonus = 0.0
            if ent:
                attrs = ent.attributes
                if attrs.get("watchlist"):
                    bonus += 0.3
                if attrs.get("prior_arrests", 0) > 0:
                    bonus += min(0.2, 0.05 * attrs["prior_arrests"])
                if attrs.get("suspicious_flag"):
                    bonus += 0.15
            risk = min(1.0, base + bonus)
            if ent:
                ent.risk_score = risk
                self.G.nodes[row["id"]]["risk_score"] = risk
            scores.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "entity_type": row["entity_type"],
                    "risk_score": round(risk, 4),
                    "community": communities.get(row["id"], -1),
                    "betweenness_centrality": row["betweenness_centrality"],
                }
            )
        return pd.DataFrame(scores).sort_values("risk_score", ascending=False)

    def suspicious_relationships(self, min_weight: float = 2.0) -> list[dict]:
        """Flag high-weight or cross-community edges."""
        communities = self.community_detection()
        flags = []
        for u, v, data in self.G.edges(data=True):
            weight = data.get("weight", 1.0)
            cross = communities.get(u, -1) != communities.get(v, -1)
            if weight >= min_weight or (cross and weight >= 1.5):
                flags.append(
                    {
                        "source": u,
                        "target": v,
                        "rel_type": data.get("rel_type", ""),
                        "weight": weight,
                        "cross_community": cross,
                        "reason": "high_weight" if weight >= min_weight else "cross_community",
                    }
                )
        return sorted(flags, key=lambda x: -x["weight"])

    def search_entities(self, query: str) -> list[Entity]:
        q = query.lower()
        return [
            e
            for e in self.entities.values()
            if q in e.name.lower() or q in e.id.lower() or q in e.entity_type.lower()
        ]

    def timeline_events(self) -> pd.DataFrame:
        rows = []
        for e in self.entities.values():
            if e.entity_type == "event":
                rows.append(
                    {
                        "id": e.id,
                        "name": e.name,
                        "date": e.attributes.get("date", ""),
                        "location": e.attributes.get("location", ""),
                        "description": e.attributes.get("description", ""),
                    }
                )
        df = pd.DataFrame(rows)
        if not df.empty and "date" in df.columns:
            df = df.sort_values("date")
        return df

    def to_plotly_figure(self):
        """Return a Plotly figure of the graph coloured by risk / community."""
        import plotly.graph_objects as go

        if self.G.number_of_nodes() == 0:
            return go.Figure()
        pos = nx.spring_layout(self.G, seed=42, weight="weight")
        edge_x, edge_y = [], []
        for u, v in self.G.edges():
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, line=dict(width=0.8, color="#888"), hoverinfo="none", mode="lines"
        )
        node_x, node_y, texts, colors, sizes = [], [], [], [], []
        for nid, (x, y) in pos.items():
            ent = self.entities.get(nid)
            risk = ent.risk_score if ent else 0
            node_x.append(x)
            node_y.append(y)
            texts.append(f"{ent.name if ent else nid}<br>type={ent.entity_type if ent else '?'}<br>risk={risk:.2f}")
            colors.append(risk)
            sizes.append(12 + 30 * risk)
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers",
            hoverinfo="text",
            text=texts,
            marker=dict(
                showscale=True,
                colorscale="YlOrRd",
                color=colors,
                size=sizes,
                colorbar=dict(title="Risk"),
                line_width=1,
            ),
        )
        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(
            title="Criminal Network Graph (node size/color = risk)",
            showlegend=False,
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600,
        )
        return fig

    def export_json(self, path: Path) -> None:
        data = {
            "entities": [asdict(e) for e in self.entities.values()],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "rel_type": d.get("rel_type"),
                    "weight": d.get("weight", 1.0),
                }
                for u, v, d in self.G.edges(data=True)
            ],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def import_json(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in data.get("entities", []):
            self.add_entity(Entity(**e))
        for edge in data.get("edges", []):
            self.add_relationship(
                Relationship(
                    source=edge["source"],
                    target=edge["target"],
                    rel_type=edge.get("rel_type", "linked"),
                    weight=edge.get("weight", 1.0),
                )
            )
