"""Core graph construction and explainable network analytics for LinkLens."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any
import math
import networkx as nx
import pandas as pd

MAX_ROWS = 100_000
ENTITY_TYPES = {"person", "organization", "account", "phone", "location", "vehicle", "event", "unknown"}

@dataclass
class GraphBundle:
    graph: nx.Graph
    source_label: str = "Uploaded data"
    warnings: list[str] = field(default_factory=list)

def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value): return default
    except (TypeError, ValueError): pass
    value = str(value).strip()
    return value or default

def _date(value: Any) -> str:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return "" if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")

def _weight(value: Any) -> float:
    try:
        n = float(value)
        return min(1_000_000.0, max(0.01, n)) if math.isfinite(n) else 1.0
    except (TypeError, ValueError): return 1.0

def build_from_interactions(frame: pd.DataFrame, source_col: str, target_col: str,
    relationship_col: str | None = None, date_col: str | None = None,
    weight_col: str | None = None, source_name_col: str | None = None,
    target_name_col: str | None = None, source_label: str = "Uploaded interactions") -> GraphBundle:
    if frame.empty: raise ValueError("The interactions file is empty. Add at least one row.")
    if len(frame) > MAX_ROWS: raise ValueError(f"The file exceeds the {MAX_ROWS:,}-row limit.")
    if source_col not in frame or target_col not in frame: raise ValueError("Choose valid source and target columns.")
    if source_col == target_col: raise ValueError("Source and target must be different columns.")
    graph, skipped = nx.Graph(), 0
    for _, row in frame.iterrows():
        a, b = _clean(row.get(source_col)), _clean(row.get(target_col))
        if not a or not b: skipped += 1; continue
        an = _clean(row.get(source_name_col), a) if source_name_col else a
        bn = _clean(row.get(target_name_col), b) if target_name_col else b
        graph.add_node(a, name=an, label=an, entity_type="person", type="person")
        graph.add_node(b, name=bn, label=bn, entity_type="person", type="person")
        rel = _clean(row.get(relationship_col), "contact") if relationship_col else "contact"
        day = _date(row.get(date_col)) if date_col else ""
        strength = _weight(row.get(weight_col)) if weight_col else 1.0
        if graph.has_edge(a, b):
            edge = graph[a][b]; edge["weight"] += strength; edge["interaction_count"] += 1
            if day and day >= edge.get("date", ""): edge["date"], edge["relationship"], edge["rel_type"] = day, rel, rel
        else: graph.add_edge(a, b, weight=strength, relationship=rel, rel_type=rel, date=day, interaction_count=1)
    if not graph.number_of_edges(): raise ValueError("No usable relationships found. Check the mapped columns.")
    warnings = [f"Skipped {skipped} rows with a missing endpoint."] if skipped else []
    graph.graph["interaction_rows"] = len(frame) - skipped
    return GraphBundle(graph, source_label, warnings)

def build_from_nodes_edges(nodes: pd.DataFrame, edges: pd.DataFrame, node_id_col: str,
    edge_source_col: str, edge_target_col: str, node_name_col: str | None = None,
    node_type_col: str | None = None, relationship_col: str | None = None,
    date_col: str | None = None, weight_col: str | None = None,
    source_label: str = "Uploaded entities and relationships") -> GraphBundle:
    if nodes.empty or edges.empty: raise ValueError("Both entity and relationship files need at least one row.")
    if len(nodes) > MAX_ROWS or len(edges) > MAX_ROWS: raise ValueError(f"Each file must be under {MAX_ROWS:,} rows.")
    if node_id_col not in nodes: raise ValueError("Choose a valid entity ID column.")
    if edge_source_col == edge_target_col: raise ValueError("Relationship source and target must be different columns.")
    graph = nx.Graph()
    for _, row in nodes.iterrows():
        nid = _clean(row.get(node_id_col))
        if not nid: continue
        name = _clean(row.get(node_name_col), nid) if node_name_col else nid
        kind = _clean(row.get(node_type_col), "unknown").lower() if node_type_col else "unknown"
        if kind not in ENTITY_TYPES: kind = "unknown"
        graph.add_node(nid, name=name, label=name, entity_type=kind, type=kind,
                       **{str(k): _clean(v) for k, v in row.items() if k not in {node_id_col, node_name_col, node_type_col} and _clean(v)})
    skipped = 0
    for _, row in edges.iterrows():
        a, b = _clean(row.get(edge_source_col)), _clean(row.get(edge_target_col))
        if not a or not b: skipped += 1; continue
        for nid in (a,b):
            if nid not in graph: graph.add_node(nid, name=nid, label=nid, entity_type="unknown", type="unknown")
        rel = _clean(row.get(relationship_col), "linked") if relationship_col else "linked"
        day = _date(row.get(date_col)) if date_col else ""
        strength = _weight(row.get(weight_col)) if weight_col else 1.0
        if graph.has_edge(a,b):
            graph[a][b]["weight"] += strength; graph[a][b]["interaction_count"] += 1
            if day and day >= graph[a][b].get("date", ""): graph[a][b]["date"] = day
        else: graph.add_edge(a,b,weight=strength,relationship=rel,rel_type=rel,date=day,interaction_count=1)
    if not graph.number_of_edges(): raise ValueError("No connected relationships found in the mapped files.")
    warnings = [f"Skipped {skipped} relationship rows with missing endpoints."] if skipped else []
    return GraphBundle(graph, source_label, warnings)

def sample_case() -> GraphBundle:
    """Build a deterministic fictional case (no real people or real identifiers)."""
    g = nx.Graph(); start = date(2025, 1, 5)
    names = ["Mara Vale", "Elias North", "Tessa Rowan", "Owen Mercer", "Iris Bell", "Caleb Frost", "Sofia Lane", "Noah Pike", "Lena Hart", "Adrian Wells", "Nadia Cross", "Felix Stone", "Amara West", "Theo Grant", "Mina Cole", "Arlo Finch", "Vera Sloan", "Dylan Shaw", "Esme Reed", "Ruben Chase", "Cleo Parks", "Ezra Blake", "Nina Shore", "Kian Brooks", "Luca Hayes", "Maya Quinn", "Seth Rivers", "Ari Moss"]
    roles = ["coordinator", "route lead", "communications contact", "courier", "logistics contact", "courier", "finance contact", "driver"]
    for i, name in enumerate(names,1):
        group = "Harbor" if i <= 10 else "Inland" if i <= 19 else "Transit"
        g.add_node(f"P{i:02}", name=name, label=name, entity_type="person", type="person", role=roles[(i-1)%len(roles)], group=group, fictional=True)
    extras = [("ORG01","Northstar Freight","organization","Harbor"),("ORG02","Blue Lantern Imports","organization","Harbor"),("ORG03","Cedarline Trading","organization","Inland"),("ORG04","Westbridge Storage","organization","Inland"),("ORG05","Silver Current Transport","organization","Transit"),("ORG06","Juniper Commercial","organization","Transit")]
    for i in range(1,6): extras.append((f"ACC{i:02}",f"Synthetic ledger {8100+i*73}","account",["Harbor","Inland","Transit"][(i-1)%3]))
    for i in range(1,6): extras.append((f"PH{i:02}",f"Phone 555-01{i:02}","phone",["Harbor","Inland","Transit"][(i-1)%3]))
    for i,n in enumerate(["Pier 4 warehouse","East market depot","Cedar road lot","Airport freight bay"],1): extras.append((f"LOC{i:02}",n,"location",["Harbor","Inland","Transit"][(i-1)%3]))
    for i,n in enumerate(["Van QL-204","Truck NR-118","Van TM-907"],1): extras.append((f"VEH{i:02}",n,"vehicle",["Harbor","Inland","Transit"][(i-1)%3]))
    for nid,name,kind,group in extras: g.add_node(nid,name=name,label=name,entity_type=kind,type=kind,group=group,fictional=True)
    counter=0
    def link(a,b,rel,weight=1.0,offset=None):
        nonlocal counter
        counter+=1; day=(start+timedelta(days=offset if offset is not None else (counter*3+(counter%7)*2)%175)).isoformat()
        if g.has_edge(a,b):
            e=g[a][b]; e["weight"]+=weight; e["interaction_count"]+=1
            if day>=e.get("date",""): e.update(date=day,relationship=rel,rel_type=rel)
        else: g.add_edge(a,b,weight=weight,relationship=rel,rel_type=rel,date=day,interaction_count=1,evidence="Fictional sample event")
    for lo,hi,leader in [(1,10,2),(11,19,11),(20,28,20)]:
        for i in range(lo,hi+1):
            for j in range(i+1,min(hi,i+2)+1): link(f"P{i:02}",f"P{j:02}","repeated contact" if j==i+1 else "shared trip",1.0+((i+j)%3)*.35)
        for i in range(lo,hi+1):
            if i!=leader and (i+leader)%3==0: link(f"P{leader:02}",f"P{i:02}","coordination",1.4)
    for leader in (2,11,20): link("P01",f"P{leader:02}","coordination",2.2,24+leader)
    for a,b in [("P03","P12"),("P08","P22"),("P15","P24"),("P06","P20")]: link(a,b,"cross-group contact",1.25)
    attachments=[("ORG01",[2,3,5,7]),("ORG02",[4,9,10]),("ORG03",[11,12,15,19]),("ORG04",[13,17,18]),("ORG05",[20,22,24,27]),("ORG06",[21,25,28]),("ACC01",[3,7,12]),("ACC02",[8,14,21]),("ACC03",[16,18,25]),("ACC04",[2,23,26]),("ACC05",[10,19,27]),("PH01",[2,4,8]),("PH02",[6,9,13]),("PH03",[11,16,18]),("PH04",[20,22,26]),("PH05",[23,25,28]),("LOC01",[2,5,8]),("LOC02",[11,14,17]),("LOC03",[20,23,27]),("LOC04",[4,15,24]),("VEH01",[4,8,10]),("VEH02",[13,17,22]),("VEH03",[21,24,28])]
    for entity, people in attachments:
        for person in people: link(entity,f"P{person:02}","shared resource" if entity.startswith(("ACC","PH")) else "associated with",1.1+(counter%3)*.3)
    for a,b in [("ORG01","LOC01"),("ORG03","LOC02"),("ORG05","LOC03"),("ORG02","ORG04"),("ORG04","ORG06")]: link(a,b,"business overlap",1.2)
    g.graph["interaction_rows"]=counter
    return GraphBundle(g,"Fictional sample case · Operation Lantern")

def analyze(bundle: GraphBundle) -> dict[str, Any]:
    g=bundle.graph
    if not g.number_of_nodes(): raise ValueError("The network contains no entities.")
    degree = dict(g.degree())
    if g.number_of_edges() and g.number_of_nodes() > 1200:
        # Sampling keeps CPU cost manageable for larger uploads.
        between = nx.betweenness_centrality(g, k=min(200, g.number_of_nodes()), normalized=True, seed=19)
    else:
        between = nx.betweenness_centrality(g, normalized=True) if g.number_of_edges() else {n: 0 for n in g}
    close=nx.closeness_centrality(g) if g.number_of_edges() else {n:0 for n in g}
    try: influence=nx.eigenvector_centrality(g,max_iter=500,weight="weight") if g.number_of_edges() else {n:0 for n in g}
    except (nx.NetworkXException,ValueError): influence={n:0 for n in g}
    try: groups=list(nx.community.greedy_modularity_communities(g,weight="weight")) if g.number_of_edges() else [{n} for n in g]
    except (nx.NetworkXException,ZeroDivisionError): groups=[set(c) for c in nx.connected_components(g)]
    groups.sort(key=lambda c:(-len(c),sorted(map(str,c))[0])); cmap={n:i for i,c in enumerate(groups) for n in c}
    cross={n:sum(cmap.get(v)!=cmap.get(n) for v in g.neighbors(n)) for n in g}
    def scale(vals):
        lo=min(vals.values(),default=0); hi=max(vals.values(),default=0)
        return {k:(100*(v-lo)/(hi-lo) if hi>lo else (100 if hi>0 else 0)) for k,v in vals.items()}
    ds,bs,is_=scale(degree),scale({n:between[n]+cross[n]*.12 for n in g}),scale(influence)
    rows=[]
    for n,a in g.nodes(data=True):
        rows.append({"id":str(n),"name":_clean(a.get("name",a.get("label")),str(n)),"type":_clean(a.get("entity_type",a.get("type")),"unknown").lower(),"direct_links":degree[n],"betweenness":round(float(between[n]),4),"closeness":round(float(close[n]),4),"influence":round(float(influence[n]),4),"bridge_links":cross[n],"community":cmap[n],"community_name":f"Group {chr(65+cmap[n]%26)}","most_connected_score":round(ds[n],1),"bridge_score":round(bs[n],1),"influence_score":round(is_[n],1),"review_priority":round(.3*ds[n]+.35*bs[n]+.35*is_[n],1),"role":_clean(a.get("role",a.get("group")),"Unspecified")})
    metrics=pd.DataFrame(rows).sort_values(["review_priority","direct_links","name"],ascending=[False,False,True]).reset_index(drop=True)
    comm=[]
    for i,members in enumerate(groups):
        sub=g.subgraph(members); types=[_clean(g.nodes[n].get("entity_type","unknown")) for n in members]
        leader=max(members,key=lambda n:(degree[n],str(g.nodes[n].get("name",n))))
        comm.append({"community":i,"name":f"Group {chr(65+i%26)}","size":len(members),"density":round(nx.density(sub),2) if len(members)>1 else 0,"dominant_type":pd.Series(types).value_counts().index[0] if types else "entities","leader":_clean(g.nodes[leader].get("name"),str(leader)),"leader_id":str(leader),"members":sorted(map(str,members))})
    return {"metrics":metrics,"communities":comm,"community_map":cmap,"degree":degree,"betweenness":between,"influence":influence,"cross_links":cross}

def suspicious_findings(bundle: GraphBundle, result: dict[str,Any]) -> list[dict[str,Any]]:
    g=bundle.graph; m=result["metrics"]; out=[]
    for _,r in m[m.bridge_links>0].sort_values(["bridge_links","betweenness"],ascending=False).head(4).iterrows():
        out.append({"severity":"High" if r.bridge_links>=3 else "Moderate","title":f"{r['name']} links separate groups","evidence":f"{int(r.bridge_links)} connection(s) reach other detected communities.","why":"Cross-group connections can show how activity moves between otherwise separate circles; legitimate explanations are possible.","next":"Review source records and dates before drawing a conclusion.","entity_id":r.id})
    shared=[]
    for n,a in g.nodes(data=True):
        kind=_clean(a.get("entity_type",a.get("type"))).lower()
        if kind in {"account","phone"} and g.degree(n)>=2: shared.append((g.degree(n),_clean(a.get("name"),str(n)),str(n),kind))
    for degree,name,nid,kind in sorted(shared,reverse=True)[:4]: out.append({"severity":"High" if degree>=4 else "Moderate","title":f"Shared {kind} connects {degree} entities","evidence":f"{name} is linked to {degree} entities.","why":"Shared identifiers can indicate a common resource, but may also reflect routine legitimate use.","next":"Check ownership, time overlap and source reliability.","entity_id":nid})
    order={"High":0,"Moderate":1,"Low":2}; return sorted(out,key=lambda x:(order[x["severity"]],x["title"]))

def likely_hidden_links(bundle: GraphBundle, top_k: int=8) -> pd.DataFrame:
    g=bundle.graph; rows=[]
    if g.number_of_nodes()<3:return pd.DataFrame(columns=["Entity A","Entity B","Shared contacts","Structural confidence"])
    for a,b,score in nx.jaccard_coefficient(g):
        if score<=0:continue
        common=sorted(set(g.neighbors(a))&set(g.neighbors(b)))
        rows.append({"Entity A":_clean(g.nodes[a].get("name"),str(a)),"Entity B":_clean(g.nodes[b].get("name"),str(b)),"Shared contacts":", ".join(_clean(g.nodes[n].get("name"),str(n)) for n in common[:4]),"Structural confidence":round(float(score)*100,1),"_score":score})
    rows.sort(key=lambda r:(-r["_score"],r["Entity A"],r["Entity B"]))
    return pd.DataFrame([{k:v for k,v in r.items() if k!="_score"} for r in rows[:top_k]],columns=["Entity A","Entity B","Shared contacts","Structural confidence"])

def timeline_frame(bundle: GraphBundle) -> pd.DataFrame:
    dates=[_date(a.get("date")) for _,_,a in bundle.graph.edges(data=True) if _date(a.get("date"))]
    if not dates:return pd.DataFrame(columns=["Date","Interactions"])
    return pd.Series(dates).value_counts().sort_index().rename_axis("Date").reset_index(name="Interactions")

def graph_stats(bundle: GraphBundle) -> dict[str,int]:
    g=bundle.graph
    return {"entities":g.number_of_nodes(),"relationships":g.number_of_edges(),"components":nx.number_connected_components(g) if g.number_of_nodes() else 0,"dated_relationships":sum(bool(_date(a.get("date"))) for _,_,a in g.edges(data=True)),"isolated_entities":len(list(nx.isolates(g)))}
