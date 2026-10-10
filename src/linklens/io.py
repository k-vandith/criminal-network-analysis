"""File readers, templates, and standalone report exports for LinkLens."""
from __future__ import annotations
import json
import html
from io import BytesIO
from typing import Any
import pandas as pd
from .core import GraphBundle, build_from_interactions, build_from_nodes_edges

def read_table(upload) -> pd.DataFrame:
    name = upload.name.lower()
    raw = upload.getvalue()
    if len(raw) > 50 * 1024 * 1024: raise ValueError("File exceeds the 50 MB upload limit.")
    try:
        if name.endswith(".csv"): frame = pd.read_csv(BytesIO(raw), nrows=100_001)
        elif name.endswith(".json"):
            data = json.loads(raw.decode("utf-8-sig"))
            if isinstance(data, list): frame = pd.DataFrame(data)
            elif isinstance(data, dict):
                items = data.get("interactions", data.get("edges", data.get("relationships", data.get("entities", data.get("nodes", [])))))
                frame = pd.DataFrame(items)
            else: raise ValueError("JSON should contain a list of records or an object with nodes/edges.")
        else: raise ValueError("Use a CSV or JSON file.")
    except (UnicodeDecodeError, json.JSONDecodeError, pd.errors.ParserError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(("Use a", "JSON should")): raise
        raise ValueError("Could not read this file. Check that it is valid UTF-8 CSV or JSON.") from exc
    if frame.empty: raise ValueError("The file contains no rows.")
    if len(frame) > 100_000: raise ValueError("This file has more than 100,000 rows; reduce it and try again.")
    return frame

def auto_col(frame: pd.DataFrame, candidates: tuple[str,...], fallback: int = 0) -> str:
    lookup={str(c).strip().lower():str(c) for c in frame.columns}
    for c in candidates:
        if c in lookup:return lookup[c]
    return str(frame.columns[min(fallback,len(frame.columns)-1)])

def bundle_from_json(raw: bytes, label: str) -> GraphBundle:
    try: data=json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise ValueError("This JSON file is invalid or not UTF-8.") from exc
    if isinstance(data,list): frame=pd.DataFrame(data); nodes=pd.DataFrame(); edges=frame
    elif isinstance(data,dict):
        nodes=data.get("entities",data.get("nodes",[])); edges=data.get("edges",data.get("relationships",data.get("interactions",[])))
        if not isinstance(nodes,list) or not isinstance(edges,list):raise ValueError("JSON nodes and edges must be arrays.")
        edges=pd.DataFrame(edges); nodes=pd.DataFrame(nodes)
    else:raise ValueError("JSON must be a list of interactions or an object with nodes and edges.")
    if edges.empty:raise ValueError("No relationships were found in this JSON file.")
    if nodes.empty:
        a=auto_col(edges,("source","from","caller","sender","entity_a","account_from"),0); b=auto_col(edges,("target","to","receiver","recipient","entity_b","account_to"),min(1,len(edges.columns)-1))
        rel=next((str(c) for c in edges.columns if str(c).lower() in {"relationship","rel_type","relationship_type","type","event"}),None)
        day=next((str(c) for c in edges.columns if str(c).lower() in {"date","timestamp","datetime","time"}),None)
        weight=next((str(c) for c in edges.columns if str(c).lower() in {"weight","strength","amount","count"}),None)
        return build_from_interactions(edges,a,b,rel,day,weight,source_label=label)
    ni=auto_col(nodes,("id","entity_id","node_id","identifier"),0); nn=next((str(c) for c in nodes.columns if str(c).lower() in {"name","label","display_name"}),None); nt=next((str(c) for c in nodes.columns if str(c).lower() in {"entity_type","type","kind","category"}),None)
    a=auto_col(edges,("source","from","source_id","u","entity_a"),0); b=auto_col(edges,("target","to","target_id","v","entity_b"),min(1,len(edges.columns)-1))
    rel=next((str(c) for c in edges.columns if str(c).lower() in {"relationship","rel_type","relationship_type","type"}),None); day=next((str(c) for c in edges.columns if str(c).lower() in {"date","timestamp","datetime","time"}),None); weight=next((str(c) for c in edges.columns if str(c).lower() in {"weight","strength","amount","count"}),None)
    return build_from_nodes_edges(nodes,edges,ni,a,b,nn,nt,rel,day,weight,label)

def template_csv() -> bytes:
    return b"source,target,relationship,date,weight\nMara Vale,Elias North,phone contact,2025-02-04,2\nElias North,Northstar Freight,associated with,2025-02-07,1\nMara Vale,Northstar Freight,coordination,2025-02-09,3\n"

def report_html(bundle: GraphBundle, analysis: dict[str,Any], findings: list[dict[str,Any]]) -> str:
    stats=bundle.graph.number_of_nodes(),bundle.graph.number_of_edges()
    top=analysis["metrics"].head(10)
    rows="".join(f"<tr><td>{html.escape(str(r['name']))}</td><td>{html.escape(str(r['type']))}</td><td>{r['direct_links']}</td><td>{r['bridge_links']}</td><td>{r['review_priority']:.1f}/100</td></tr>" for _,r in top.iterrows())
    cards="".join(f"<article><strong>{html.escape(str(f['severity']))} · {html.escape(str(f['title']))}</strong><p>{html.escape(str(f['evidence']))}</p><p><b>Why review:</b> {html.escape(str(f['why']))}</p><p><b>Next step:</b> {html.escape(str(f['next']))}</p></article>" for f in findings[:12]) or "<p>No heuristic patterns were raised by the current rules.</p>"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LinkLens case report</title><style>body{{font:16px/1.55 Inter,Segoe UI,sans-serif;background:#f6f7fb;color:#202436;margin:0}}main{{max-width:1050px;margin:auto;padding:32px}}header{{background:#17192a;color:white;padding:28px;border-radius:16px}}h1{{margin:0}}small{{color:#aeb2d5}}section,article{{background:white;border:1px solid #e1e4ee;border-radius:12px;padding:20px;margin:16px 0}}.kpis{{display:flex;gap:12px;flex-wrap:wrap}}.kpis div{{background:#f0efff;padding:14px 18px;border-radius:10px;min-width:140px}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #e5e7ef}}th{{background:#f0efff}}footer{{color:#6c7187;font-size:13px}}</style></head><body><main><header><small>NETWORK INTELLIGENCE · OFFLINE REPORT</small><h1>LinkLens case summary</h1><p>{html.escape(str(bundle.source_label))}</p><small>Generated from the currently loaded graph. Fictional/demo results are illustrative.</small></header><section><h2>At a glance</h2><div class="kpis"><div><b>{stats[0]}</b><br>entities</div><div><b>{stats[1]}</b><br>relationships</div><div><b>{len(analysis['communities'])}</b><br>detected groups</div><div><b>{len(findings)}</b><br>review signals</div></div><p>These are structural indicators to help prioritize review. They are not proof of criminal activity or guilt.</p></section><section><h2>Key entities</h2><table><thead><tr><th>Entity</th><th>Type</th><th>Direct links</th><th>Bridge links</th><th>Review priority</th></tr></thead><tbody>{rows}</tbody></table></section><section><h2>Patterns to review</h2>{cards}</section><section><h2>Suggested workflow</h2><ol><li>Confirm the provenance and completeness of source records.</li><li>Open the relationships behind each signal.</li><li>Compare dates, entity identifiers and alternative explanations.</li><li>Record conclusions separately from automated heuristics.</li></ol></section><footer>LinkLens · Local-first analysis · Do not treat structural scores as legal evidence.</footer></main></body></html>'''
