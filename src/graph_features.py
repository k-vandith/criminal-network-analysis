"""Advanced analyst features monkey-patched onto CriminalNetworkGraph.

The module keeps the original public API while adding explainable,
investigator-facing analytics: bridges, anomalies, community profiles,
entity profiles, shortest paths, and robust analytical-priority ranking.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)


def _numeric(series: pd.Series | Any, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _centrality_frame(self) -> pd.DataFrame:
    """Compute degree, weighted betweenness, closeness, and eigenvector centrality."""
    columns = [
        "id", "name", "entity_type", "degree_centrality",
        "betweenness_centrality", "closeness_centrality",
        "eigenvector_centrality",
    ]
    if self.G.number_of_nodes() == 0:
        return pd.DataFrame(columns=columns)

    degree = nx.degree_centrality(self.G)
    betweenness = nx.betweenness_centrality(self.G, weight="weight", normalized=True)
    closeness = nx.closeness_centrality(self.G)
    try:
        eigenvector = nx.eigenvector_centrality(
            self.G, max_iter=1000, tol=1e-06, weight="weight"
        )
    except (nx.PowerIterationFailedConvergence, ValueError, nx.NetworkXException):
        try:
            eigenvector = nx.eigenvector_centrality_numpy(self.G, weight="weight")
        except Exception:
            logger.warning("Eigenvector centrality failed; using zeros")
            eigenvector = {node: 0.0 for node in self.G.nodes}

    rows = []
    for nid in self.G.nodes:
        ent = self.entities.get(nid)
        rows.append(
            {
                "id": nid,
                "name": ent.name if ent else str(nid),
                "entity_type": ent.entity_type if ent else "unknown",
                "degree_centrality": round(float(degree.get(nid, 0.0)), 6),
                "betweenness_centrality": round(float(betweenness.get(nid, 0.0)), 6),
                "closeness_centrality": round(float(closeness.get(nid, 0.0)), 6),
                "eigenvector_centrality": round(float(eigenvector.get(nid, 0.0)), 6),
            }
        )
    return pd.DataFrame(rows)


def link_prediction(self, top_k: int = 10) -> pd.DataFrame:
    columns = ["source", "target", "source_name", "target_name", "score", "method"]
    if self.G.number_of_nodes() < 2:
        return pd.DataFrame(columns=columns)

    preds: dict[tuple[str, str], float] = {}
    try:
        for u, v, p in nx.resource_allocation_index(self.G):
            a, b = sorted((u, v))
            preds[(a, b)] = preds.get((a, b), 0.0) + float(p)
    except Exception as exc:
        logger.warning("Resource allocation prediction failed: %s", exc)
    try:
        for u, v, p in nx.jaccard_coefficient(self.G):
            a, b = sorted((u, v))
            preds[(a, b)] = preds.get((a, b), 0.0) + 0.5 * float(p)
    except Exception as exc:
        logger.warning("Jaccard prediction failed: %s", exc)

    method = "resource_allocation+jaccard"
    if not preds:
        method = "preferential_attachment"
        try:
            for u, v, p in nx.preferential_attachment(self.G):
                a, b = sorted((u, v))
                preds[(a, b)] = float(p)
        except Exception as exc:
            logger.warning("Preferential attachment prediction failed: %s", exc)

    rows = []
    for (a, b), score in preds.items():
        if score <= 0:
            continue
        rows.append(
            {
                "source": a,
                "target": b,
                "source_name": self.entities[a].name if a in self.entities else str(a),
                "target_name": self.entities[b].name if b in self.entities else str(b),
                "score": round(score, 6),
                "method": method,
            }
        )
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df
    return df.sort_values("score", ascending=False).head(top_k).reset_index(drop=True)


def key_player_ranking(
    self,
    top_k: int = 10,
) -> pd.DataFrame:
    """Rank entities by explainable analytical priority."""

    output_columns = [
        "rank",
        "id",
        "name",
        "entity_type",
        "kingpin_score",
        "risk_score",
        "betweenness_centrality",
        "degree_centrality",
        "community",
    ]

    risk = self.compute_risk_scores()

    if risk is None or risk.empty:
        return pd.DataFrame(columns=output_columns)

    cent = self.centrality_analysis()

    if cent is None or cent.empty:
        cent = pd.DataFrame(
            {
                "id": list(self.G.nodes),
                "degree_centrality": 0.0,
                "betweenness_centrality": 0.0,
                "eigenvector_centrality": 0.0,
            }
        )

    # IMPORTANT:
    # compute_risk_scores() already contains betweenness_centrality.
    # Remove overlapping centrality columns from risk before merging so
    # pandas does not create _x / _y suffixes.
    risk_clean = risk.drop(
        columns=[
            "degree_centrality",
            "betweenness_centrality",
            "eigenvector_centrality",
        ],
        errors="ignore",
    )

    centrality_clean = cent[
        [
            "id",
            "degree_centrality",
            "betweenness_centrality",
            "eigenvector_centrality",
        ]
    ].copy()

    merged = risk_clean.merge(
        centrality_clean,
        on="id",
        how="left",
    )

    # Make sure every required numeric column exists.
    numeric_columns = [
        "risk_score",
        "degree_centrality",
        "betweenness_centrality",
        "eigenvector_centrality",
    ]

    for column in numeric_columns:
        if column not in merged.columns:
            merged[column] = 0.0

        merged[column] = pd.to_numeric(
            merged[column],
            errors="coerce",
        ).fillna(0.0)

    merged["kingpin_score"] = (
        0.40 * merged["risk_score"]
        + 0.30 * merged["betweenness_centrality"]
        + 0.20 * merged["degree_centrality"]
        + 0.10 * merged["eigenvector_centrality"]
    ).round(4)

    merged = merged.sort_values(
        "kingpin_score",
        ascending=False,
    ).head(top_k).copy()

    merged["rank"] = range(
        1,
        len(merged) + 1,
    )

    if "community" not in merged.columns:
        merged["community"] = -1

    if "name" not in merged.columns:
        merged["name"] = merged["id"].astype(str)

    if "entity_type" not in merged.columns:
        merged["entity_type"] = "unknown"

    return merged[
        output_columns
    ].reset_index(drop=True)


def bridge_entities(self, top_k: int = 15) -> pd.DataFrame:
    """Find entities that connect otherwise different communities."""
    columns = [
        "id", "name", "entity_type", "community", "degree",
        "cross_community_links", "bridge_ratio",
    ]
    if self.G.number_of_nodes() == 0:
        return pd.DataFrame(columns=columns)
    communities = self.community_detection()
    rows = []
    for nid in self.G.nodes:
        neighbors = list(self.G.neighbors(nid))
        degree = len(neighbors)
        cross = sum(1 for n in neighbors if communities.get(n, -1) != communities.get(nid, -1))
        ent = self.entities.get(nid)
        rows.append(
            {
                "id": nid,
                "name": ent.name if ent else str(nid),
                "entity_type": ent.entity_type if ent else "unknown",
                "community": communities.get(nid, -1),
                "degree": degree,
                "cross_community_links": cross,
                "bridge_ratio": round(cross / degree, 4) if degree else 0.0,
            }
        )
    df = pd.DataFrame(rows, columns=columns)
    return df.sort_values(
        ["cross_community_links", "bridge_ratio", "degree"],
        ascending=False,
    ).head(top_k).reset_index(drop=True)


def community_summary(self) -> pd.DataFrame:
    """Return one row per detected community with interpretable statistics."""
    mapping = self.community_detection()
    if not mapping:
        return pd.DataFrame()

    groups: dict[int, list[str]] = {}
    for nid, cid in mapping.items():
        groups.setdefault(cid, []).append(nid)

    rows = []
    for cid, nodes in sorted(groups.items()):
        sub = self.G.subgraph(nodes)
        types = pd.Series(
            [self.entities[n].entity_type for n in nodes if n in self.entities]
        ).value_counts()
        leader = None
        leader_score = -1.0
        for node in nodes:
            score = float(sub.degree(node, weight="weight"))
            if score > leader_score:
                leader, leader_score = node, score
        rows.append(
            {
                "community": cid,
                "entities": len(nodes),
                "relationships": sub.number_of_edges(),
                "density": round(nx.density(sub), 4) if len(nodes) > 1 else 0.0,
                "dominant_type": types.index[0] if not types.empty else "unknown",
                "core_entity": self.entities[leader].name if leader in self.entities else str(leader),
                "core_degree_weight": round(leader_score, 2),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["entities", "relationships"], ascending=False
    ).reset_index(drop=True)


def anomaly_detection(self, top_k: int = 15) -> pd.DataFrame:
    """Explainable degree/relationship anomalies using z-scores."""
    if self.G.number_of_nodes() == 0:
        return pd.DataFrame()

    degrees = pd.Series(dict(self.G.degree()), dtype=float)
    weights = pd.Series(
        {n: float(self.G.degree(n, weight="weight")) for n in self.G.nodes},
        dtype=float,
    )
    mean_d, std_d = degrees.mean(), degrees.std(ddof=0)
    mean_w, std_w = weights.mean(), weights.std(ddof=0)
    std_d = std_d if std_d > 1e-12 else 1.0
    std_w = std_w if std_w > 1e-12 else 1.0

    rows = []
    for nid in self.G.nodes:
        ent = self.entities.get(nid)
        degree_z = (degrees[nid] - mean_d) / std_d
        weight_z = (weights[nid] - mean_w) / std_w
        score = max(0.0, degree_z, weight_z)
        reason = (
            "weighted relationship concentration"
            if weight_z >= degree_z
            else "unusual connection count"
        )
        rows.append(
            {
                "id": nid,
                "name": ent.name if ent else str(nid),
                "entity_type": ent.entity_type if ent else "unknown",
                "degree": int(degrees[nid]),
                "weighted_degree": round(float(weights[nid]), 2),
                "anomaly_score": round(float(score), 4),
                "reason": reason,
            }
        )
    return pd.DataFrame(rows).sort_values("anomaly_score", ascending=False).head(top_k).reset_index(drop=True)


def entity_profile(self, entity_id: str) -> dict[str, Any] | None:
    """Return a compact, explainable profile for one entity."""
    if entity_id not in self.G:
        return None

    ent = self.entities.get(entity_id)
    communities = self.community_detection()
    cent = _centrality_frame(self)
    row = cent[cent["id"] == entity_id]
    c = row.iloc[0].to_dict() if not row.empty else {}
    risk_df = self.compute_risk_scores()
    r = risk_df[risk_df["id"] == entity_id] if not risk_df.empty and "id" in risk_df.columns else risk_df
    risk = (
        float(r["risk_score"].iloc[0])
        if not r.empty and "risk_score" in r.columns
        else float(self.G.nodes[entity_id].get("risk_score", 0.0))
    )
    neighbors = []
    for n in self.G.neighbors(entity_id):
        other = self.entities.get(n)
        neighbors.append(
            {
                "id": n,
                "name": other.name if other else str(n),
                "entity_type": other.entity_type if other else "unknown",
                "relationship": self.G.edges[entity_id, n].get("rel_type", "linked"),
                "weight": self.G.edges[entity_id, n].get("weight", 1.0),
            }
        )

    reasons = []
    if risk >= 0.75:
        reasons.append("high analytical risk score")
    if float(c.get("betweenness_centrality", 0) or 0) >= 0.5:
        reasons.append("strong network-broker position")
    if len(neighbors) >= 5:
        reasons.append("high number of direct relationships")
    if ent and ent.attributes.get("watchlist"):
        reasons.append("watchlist attribute present in supplied data")
    if ent and ent.attributes.get("suspicious_flag"):
        reasons.append("suspicious flag present in supplied data")

    return {
        "id": entity_id,
        "name": ent.name if ent else str(entity_id),
        "entity_type": ent.entity_type if ent else "unknown",
        "risk_score": round(risk, 4),
        "community": communities.get(entity_id, -1),
        "attributes": ent.attributes if ent else {},
        "centrality": c,
        "neighbors": sorted(neighbors, key=lambda x: -float(x["weight"])),
        "reasons": reasons,
    }


def shortest_investigation_path(self, source: str, target: str) -> pd.DataFrame:
    """Find an unweighted shortest relationship path between two entities."""
    columns = ["step", "id", "name", "entity_type", "relationship_from_previous"]
    if source not in self.G or target not in self.G:
        return pd.DataFrame(columns=columns)
    try:
        path = nx.shortest_path(self.G, source=source, target=target)
    except nx.NetworkXNoPath:
        return pd.DataFrame(columns=columns)

    rows = []
    for i, nid in enumerate(path):
        ent = self.entities.get(nid)
        rel = "—"
        if i:
            rel = self.G.edges[path[i - 1], nid].get("rel_type", "linked")
        rows.append(
            {
                "step": i,
                "id": nid,
                "name": ent.name if ent else str(nid),
                "entity_type": ent.entity_type if ent else "unknown",
                "relationship_from_previous": rel,
            }
        )
    return pd.DataFrame(rows)


def key_player_explanations(self, top_k: int = 10) -> pd.DataFrame:
    ranking = self.key_player_ranking(top_k).copy()
    if ranking.empty:
        return ranking
    profiles = {row["id"]: self.entity_profile(row["id"]) for _, row in ranking.iterrows()}
    ranking["why_flagged"] = [
        "; ".join(profiles[row["id"]]["reasons"][:4])
        if profiles.get(row["id"]) and profiles[row["id"]]["reasons"]
        else "high composite analytical priority"
        for _, row in ranking.iterrows()
    ]
    return ranking


def to_pyvis_html(self, path: Path | None = None, height: str = "620px") -> str:
    path = path or Path("data/sample/network_interactive.html")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from pyvis.network import Network

        net = Network(height=height, width="100%", bgcolor="#0b1020", font_color="#eaf0ff")
        net.barnes_hut()
        communities = self.community_detection()
        for nid, data in self.G.nodes(data=True):
            ent = self.entities.get(nid)
            risk = float(data.get("risk_score", ent.risk_score if ent else 0.0))
            risk = max(0.0, min(1.0, risk))
            net.add_node(
                nid,
                label=data.get("name", nid),
                title=f"{data.get('name', nid)}<br>Analytical risk: {risk:.2f}",
                value=10 + 40 * risk,
                group=communities.get(nid, 0),
            )
        for u, v, d in self.G.edges(data=True):
            net.add_edge(
                u,
                v,
                title=d.get("rel_type", "linked"),
                value=float(d.get("weight", 1.0)),
            )
        net.save_graph(str(path))
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("pyvis unavailable (%s)", exc)
        html = "<html><body><h3>Interactive graph unavailable</h3></body></html>"
        path.write_text(html, encoding="utf-8")
        return html


def export_html_report(self, path: Path) -> Path:
    path = Path(path)
    risk = self.compute_risk_scores()
    kingpins = self.key_player_explanations(10)
    bridges = self.bridge_entities(10)
    anomalies = self.anomaly_detection(10)
    links = self.link_prediction(10)
    flags = pd.DataFrame(self.suspicious_relationships())
    timeline = self.timeline_events()

    def table(df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return "<p><em>None</em></p>"
        return df.to_html(index=False, border=0, classes="data")

    high = int((risk["risk_score"] >= 0.75).sum()) if not risk.empty and "risk_score" in risk.columns else 0
    html = f"""<!doctype html>
<html><head><meta charset='utf-8'/><title>Criminal Network Intelligence Report</title>
<style>
body {{ font-family: Inter, system-ui, sans-serif; margin: 0; background:#0b1020; color:#edf2ff; }}
main {{ max-width: 1200px; margin: 0 auto; padding: 36px; }}
h1 {{ margin-bottom: 4px; }} h2 {{ margin-top: 34px; color:#7dd3fc; }}
.meta {{ color:#a8b4cb; }} .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.card {{ background:#121a30; border:1px solid #26314d; border-radius:14px; padding:18px; }}
table {{ width:100%; border-collapse:collapse; background:#11192d; }}
th,td {{ padding:9px; border-bottom:1px solid #28344f; text-align:left; font-size:13px; }}
th {{ color:#b9c6df; }}
.notice {{ background:#1a233c; border-left:4px solid #38bdf8; padding:12px 16px; margin:18px 0; }}
</style></head><body><main>
<h1>Criminal Network Intelligence Report</h1>
<div class='meta'>Synthetic / analyst-assistance mode · generated from the local graph</div>
<div class='notice'>Analytical priority scores are heuristic and must not be treated as findings of guilt or legal evidence. Validate conclusions against source evidence.</div>
<div class='grid'>
<div class='card'><strong>Entities</strong><br><span style='font-size:28px'>{self.G.number_of_nodes()}</span></div>
<div class='card'><strong>Relationships</strong><br><span style='font-size:28px'>{self.G.number_of_edges()}</span></div>
<div class='card'><strong>Communities</strong><br><span style='font-size:28px'>{len(set(self.community_detection().values()))}</span></div>
<div class='card'><strong>High analytical risk</strong><br><span style='font-size:28px'>{high}</span></div>
</div>
<h2>Analytical priority</h2>{table(kingpins)}
<h2>Bridge candidates</h2>{table(bridges)}
<h2>Anomaly candidates</h2>{table(anomalies)}
<h2>Analytical risk scores</h2>{table(risk.head(25))}
<h2>Suspicious relationships</h2>{table(flags)}
<h2>Potential links</h2>{table(links)}
<h2>Timeline</h2>{table(timeline)}
</main></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def export_pdf_report(self, path: Path) -> Path:
    path = Path(path)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        ranking = self.key_player_explanations(8)
        c = canvas.Canvas(str(path), pagesize=letter)
        _, height = letter
        y = height - 48
        c.setFont("Helvetica-Bold", 15)
        c.drawString(50, y, "Criminal Network Intelligence Report")
        y -= 22
        c.setFont("Helvetica", 9)
        c.drawString(50, y, "Synthetic / analyst-assistance mode. Analytical priority is not legal evidence.")
        y -= 22
        c.drawString(50, y, f"Entities: {self.G.number_of_nodes()}    Relationships: {self.G.number_of_edges()}")
        y -= 24
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Top analytical-priority entities")
        y -= 18
        c.setFont("Helvetica", 9)
        for _, row in ranking.iterrows():
            line = f"{int(row['rank'])}. {row['name']} | priority={row['kingpin_score']:.2f} | risk={row['risk_score']:.2f}"
            c.drawString(50, y, line[:105])
            y -= 13
            if y < 48:
                c.showPage()
                y = height - 48
                c.setFont("Helvetica", 9)
        c.save()
        return path
    except Exception as exc:
        logger.warning("PDF export unavailable (%s)", exc)
        return self.export_html_report(path.with_suffix(".html"))


def network_health(self) -> dict:
    """Compact structural statistics for the workspace header."""
    n = self.G.number_of_nodes()
    m = self.G.number_of_edges()
    communities = self.community_detection()
    components = list(nx.connected_components(self.G)) if n else []
    clustering = float(nx.average_clustering(self.G)) if n else 0.0
    try:
        arts = list(nx.articulation_points(self.G)) if n else []
    except Exception:
        arts = []
    diameter = None
    if n and nx.is_connected(self.G) and n <= 400:
        try:
            diameter = int(nx.diameter(self.G))
        except Exception:
            diameter = None
    weighted = {nid: float(self.G.degree(nid, weight="weight")) for nid in self.G.nodes}
    return {
        "entities": n,
        "relationships": m,
        "communities": len(set(communities.values())) if communities else 0,
        "density": round(nx.density(self.G), 4) if n > 1 else 0.0,
        "components": len(components),
        "largest_component": max((len(c) for c in components), default=0),
        "average_clustering": round(clustering, 4),
        "articulation_points": len(arts),
        "diameter": diameter,
        "weighted_degree": weighted,
    }


def weighted_investigation_path(self, source: str, target: str) -> pd.DataFrame:
    """Shortest path using inverse edge weight so stronger links are cheaper."""
    columns = ["step", "id", "name", "entity_type", "relationship_from_previous", "weight"]
    if source not in self.G or target not in self.G:
        return pd.DataFrame(columns=columns)
    work = self.G.copy()
    for _u, _v, data in work.edges(data=True):
        w = float(data.get("weight", 1.0) or 1.0)
        data["distance"] = 1.0 / max(w, 1e-6)
    try:
        path = nx.shortest_path(work, source=source, target=target, weight="distance")
    except nx.NetworkXNoPath:
        return pd.DataFrame(columns=columns)
    rows = []
    for i, nid in enumerate(path):
        ent = self.entities.get(nid)
        rel, weight = "—", None
        if i:
            edge = self.G.edges[path[i - 1], nid]
            rel = edge.get("rel_type", "linked")
            weight = edge.get("weight", 1.0)
        rows.append(
            {
                "step": i,
                "id": nid,
                "name": ent.name if ent else str(nid),
                "entity_type": ent.entity_type if ent else "unknown",
                "relationship_from_previous": rel,
                "weight": weight,
            }
        )
    return pd.DataFrame(rows)


def neighborhood(self, entity_id: str, hops: int = 2) -> list[str]:
    if entity_id not in self.G:
        return []
    nodes = {entity_id}
    frontier = {entity_id}
    for _ in range(max(1, hops)):
        nxt = set()
        for nid in frontier:
            nxt.update(self.G.neighbors(nid))
        frontier = nxt - nodes
        nodes.update(nxt)
    return sorted(nodes)


def ego_network(self, entity_id: str) -> dict:
    nodes = self.neighborhood(entity_id, 1)
    sub = self.G.subgraph(nodes)
    communities = self.community_detection()
    touched = {communities.get(n, -1) for n in nodes}
    return {
        "nodes": nodes,
        "relationships": sub.number_of_edges(),
        "communities_touched": len(touched),
    }


def apply() -> None:
    from src.graph_engine import CriminalNetworkGraph

    CriminalNetworkGraph.link_prediction = link_prediction
    CriminalNetworkGraph.key_player_ranking = key_player_ranking
    CriminalNetworkGraph.bridge_entities = bridge_entities
    CriminalNetworkGraph.community_summary = community_summary
    CriminalNetworkGraph.anomaly_detection = anomaly_detection
    CriminalNetworkGraph.entity_profile = entity_profile
    CriminalNetworkGraph.shortest_investigation_path = shortest_investigation_path
    CriminalNetworkGraph.key_player_explanations = key_player_explanations
    CriminalNetworkGraph.to_pyvis_html = to_pyvis_html
    CriminalNetworkGraph.export_html_report = export_html_report
    CriminalNetworkGraph.export_pdf_report = export_pdf_report
    CriminalNetworkGraph.network_health = network_health
    CriminalNetworkGraph.weighted_investigation_path = weighted_investigation_path
    CriminalNetworkGraph.neighborhood = neighborhood
    CriminalNetworkGraph.ego_network = ego_network


apply()
