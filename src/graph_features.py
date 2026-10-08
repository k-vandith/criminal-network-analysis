"""Extra features monkey-patched onto CriminalNetworkGraph at import time."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)


def link_prediction(self, top_k: int = 10) -> pd.DataFrame:
    if self.G.number_of_nodes() < 2:
        return pd.DataFrame(columns=["source", "target", "score", "method"])
    preds: dict[tuple[str, str], float] = {}
    try:
        for u, v, p in nx.resource_allocation_index(self.G):
            a, b = sorted((u, v))
            preds[(a, b)] = preds.get((a, b), 0.0) + float(p)
    except Exception:
        pass
    try:
        for u, v, p in nx.jaccard_coefficient(self.G):
            a, b = sorted((u, v))
            preds[(a, b)] = preds.get((a, b), 0.0) + 0.5 * float(p)
    except Exception:
        pass
    if not preds:
        for u, v, p in nx.preferential_attachment(self.G):
            a, b = sorted((u, v))
            preds[(a, b)] = float(p)
    rows = [
        {
            "source": a, "target": b,
            "source_name": self.entities[a].name if a in self.entities else a,
            "target_name": self.entities[b].name if b in self.entities else b,
            "score": round(s, 6), "method": "resource_allocation+jaccard",
        }
        for (a, b), s in preds.items() if s > 0
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("score", ascending=False).head(top_k).reset_index(drop=True)


def key_player_ranking(self, top_k: int = 10) -> pd.DataFrame:
    risk = self.compute_risk_scores()
    if risk.empty:
        return risk
    cent = self.centrality_analysis()
    merged = risk.merge(
        cent[["id", "degree_centrality", "betweenness_centrality", "eigenvector_centrality"]],
        on="id", how="left",
    )
    merged["kingpin_score"] = (
        0.40 * merged["risk_score"] + 0.30 * merged["betweenness_centrality"]
        + 0.20 * merged["degree_centrality"] + 0.10 * merged["eigenvector_centrality"]
    ).round(4)
    out = merged.sort_values("kingpin_score", ascending=False).head(top_k)
    out["rank"] = range(1, len(out) + 1)
    return out[["rank", "id", "name", "entity_type", "kingpin_score", "risk_score",
                "betweenness_centrality", "degree_centrality"]].reset_index(drop=True)


def to_pyvis_html(self, path: Path | None = None, height: str = "600px") -> str:
    path = path or Path("data/sample/network_interactive.html")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from pyvis.network import Network
        net = Network(height=height, width="100%", bgcolor="#0e1117", font_color="white")
        net.barnes_hut()
        communities = self.community_detection()
        for nid, data in self.G.nodes(data=True):
            ent = self.entities.get(nid)
            risk = float(data.get("risk_score", ent.risk_score if ent else 0))
            net.add_node(nid, label=data.get("name", nid),
                title=f"{data.get('name', nid)} risk={risk:.2f}",
                value=10 + 40 * risk,
                color=f"rgb({int(255 * risk)},{int(80 * (1 - risk))},40)",
                group=communities.get(nid, 0))
        for u, v, d in self.G.edges(data=True):
            net.add_edge(u, v, title=d.get("rel_type", ""), value=d.get("weight", 1.0))
        net.save_graph(str(path))
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("pyvis unavailable (%s)", exc)
        html = "<html><body><h3>Network (pyvis not installed)</h3><ul>"
        for nid, data in self.G.nodes(data=True):
            html += f"<li>{data.get('name', nid)}</li>"
        html += "</ul></body></html>"
        path.write_text(html, encoding="utf-8")
        return html


def export_html_report(self, path: Path) -> Path:
    risk = self.compute_risk_scores()
    kingpins = self.key_player_ranking(10)
    links = self.link_prediction(10)
    flags = self.suspicious_relationships()
    timeline = self.timeline_events()

    def table(df):
        if df is None or (hasattr(df, "empty") and df.empty):
            return "<p><em>None</em></p>"
        return df.to_html(index=False, border=0)

    html = f"""<!DOCTYPE html><html><head><meta charset=\"utf-8\"/><title>Report</title>
<style>body{{font-family:system-ui;margin:2rem;background:#111;color:#eee}}
h1,h2{{color:#f5a623}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #444;padding:.4rem}}</style></head><body>
<h1>Criminal Network Analysis Report</h1>
<p>Nodes: {self.G.number_of_nodes()} · Edges: {self.G.number_of_edges()}</p>
<h2>Key players / kingpins</h2>{table(kingpins)}
<h2>Risk scores</h2>{table(risk.head(20))}
<h2>Link predictions</h2>{table(links)}
<h2>Suspicious relationships</h2>{table(pd.DataFrame(flags))}
<h2>Timeline</h2>{table(timeline)}
</body></html>"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def export_pdf_report(self, path: Path) -> Path:
    path = Path(path)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        kingpins = self.key_player_ranking(8)
        c = canvas.Canvas(str(path), pagesize=letter)
        width, height = letter
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Criminal Network Analysis Report")
        y -= 24
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Nodes: {self.G.number_of_nodes()}  Edges: {self.G.number_of_edges()}")
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Top kingpins")
        y -= 16
        c.setFont("Helvetica", 9)
        for _, row in kingpins.iterrows():
            c.drawString(50, y, f"{int(row['rank'])}. {row['name']} score={row['kingpin_score']}")
            y -= 12
            if y < 50:
                c.showPage(); y = height - 50
        c.save()
        return path
    except Exception as exc:
        logger.warning("reportlab unavailable (%s)", exc)
        return self.export_html_report(path.with_suffix(".html"))


def apply():
    from src.graph_engine import CriminalNetworkGraph
    CriminalNetworkGraph.link_prediction = link_prediction
    CriminalNetworkGraph.key_player_ranking = key_player_ranking
    CriminalNetworkGraph.to_pyvis_html = to_pyvis_html
    CriminalNetworkGraph.export_html_report = export_html_report
    CriminalNetworkGraph.export_pdf_report = export_pdf_report


apply()
