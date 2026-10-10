"""LinkLens: polished, local-first network analysis workspace."""
from __future__ import annotations

from io import BytesIO
import html
import re
import xml.sax.saxutils as xml_escape

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .core import (
    GraphBundle, analyze, build_from_interactions, build_from_nodes_edges,
    graph_stats, likely_hidden_links, sample_case, suspicious_findings, timeline_frame,
)
from .io import auto_col, bundle_from_json, read_table, report_html, template_csv
from .theme import CSS

PAGES = [
    "Overview", "Upload & Map Columns", "Network Explorer", "Key Players",
    "Groups & Communities", "Timeline", "Suspicious Patterns", "Case Report", "Glossary",
]
PLOT_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, Segoe UI, sans-serif", "color": "#e8eaf6"},
    "margin": {"l": 8, "r": 8, "t": 45, "b": 8},
}


def _name(graph, node):
    return str(graph.nodes[node].get("name", graph.nodes[node].get("label", node)))


def _kind(graph, node):
    return str(graph.nodes[node].get("entity_type", graph.nodes[node].get("type", "unknown"))).lower()


def _rel(attrs):
    return str(attrs.get("relationship", attrs.get("rel_type", "linked")))


def _maybe_col(frame, candidates):
    lookup = {str(column).strip().lower(): str(column) for column in frame.columns}
    return next((lookup[candidate] for candidate in candidates if candidate in lookup), None)


def graph_figure(bundle: GraphBundle, analysis: dict, selected=None, node_types=None, edge_types=None, hops=1):
    graph = bundle.graph
    if not graph.number_of_nodes():
        return go.Figure()
    allowed = set(node_types or [])
    visible = [n for n in graph if not allowed or _kind(graph, n) in allowed]
    if selected in visible and hops:
        focus, frontier = {selected}, {selected}
        for _ in range(int(hops)):
            frontier = {v for n in frontier for v in graph.neighbors(n)} - focus
            focus |= frontier
        visible = [n for n in visible if n in focus]
    if len(visible) > 160:
        visible = sorted(visible, key=lambda n: (-graph.degree(n), str(n)))[:160]
        if selected in graph and selected not in visible:
            visible[-1] = selected
    sub = graph.subgraph(visible)
    positions = nx.spring_layout(sub, seed=19, weight="weight", iterations=35) if sub.number_of_nodes() > 1 else {n: (0, 0) for n in sub}
    palette = {
        "person": "#9d8cff", "organization": "#4fd1b2", "account": "#ffbd69",
        "phone": "#ff8f9b", "location": "#69b7ff", "vehicle": "#c5a3ff",
        "event": "#f0df75", "unknown": "#a8afc5",
    }
    ex, ey = [], []
    for a, b, attrs in sub.edges(data=True):
        if edge_types and _rel(attrs) not in set(edge_types):
            continue
        ex.extend([positions[a][0], positions[b][0], None])
        ey.extend([positions[a][1], positions[b][1], None])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line={"width": 1, "color": "rgba(145,155,190,.38)"}, hoverinfo="skip"))
    metrics = analysis["metrics"].set_index("id")
    nodes, colors, sizes, labels, hover = list(sub), [], [], [], []
    for node in nodes:
        row = metrics.loc[str(node)] if str(node) in metrics.index else None
        priority = float(row["review_priority"]) if row is not None else 0.0
        name = _name(graph, node)
        colors.append(palette.get(_kind(graph, node), palette["unknown"]))
        sizes.append(13 + min(graph.degree(node), 10) * 1.35 + priority * .08 + (9 if node == selected else 0))
        labels.append(name if graph.degree(node) >= 3 or node == selected else "")
        hover.append(
            f"<b>{html.escape(name)}</b><br>Type: {html.escape(_kind(graph,node).title())}"
            f"<br>Direct links: {graph.degree(node)}<br>Review priority: {priority:.1f}/100"
        )
    fig.add_trace(go.Scatter(
        x=[positions[n][0] for n in nodes], y=[positions[n][1] for n in nodes],
        mode="markers+text", text=labels, textposition="top center",
        textfont={"size": 10, "color": "#e7e9f5"}, hovertext=hover, hoverinfo="text",
        customdata=[str(n) for n in nodes],
        marker={"size": sizes, "color": colors,
                "line": {"width": [3 if n == selected else 1 for n in nodes],
                         "color": ["#fff" if n == selected else "#222638" for n in nodes]}},
    ))
    fig.update_layout(**PLOT_LAYOUT, height=570, title="Relationship map · node size reflects structural prominence",
                      xaxis={"visible": False}, yaxis={"visible": False}, showlegend=False, dragmode="pan")
    return fig


def _kpi(label, value, detail):
    st.markdown(
        f'<div class="ll-card"><div class="ll-label">{html.escape(str(label))}</div>'
        f'<div class="ll-value">{html.escape(str(value))}</div><div class="ll-help">{html.escape(detail)}</div></div>',
        unsafe_allow_html=True,
    )


def _section(title, detail):
    st.markdown(f'<div class="ll-section"><h3>{html.escape(title)}</h3><div class="ll-help">{html.escape(detail)}</div></div>', unsafe_allow_html=True)


def _invalidate():
    for key in ("ll_analysis", "ll_findings", "ll_stats", "ll_timeline"):
        st.session_state.pop(key, None)


def _set_bundle(bundle):
    st.session_state.ll_bundle = bundle
    st.session_state.ll_selected = None
    _invalidate()


def _init():
    st.session_state.setdefault("ll_bundle", sample_case())
    st.session_state.setdefault("ll_page", "Overview")
    st.session_state.setdefault("ll_selected", None)


def _derived(bundle):
    if "ll_analysis" not in st.session_state:
        result = analyze(bundle)
        st.session_state.ll_analysis = result
        st.session_state.ll_findings = suspicious_findings(bundle, result)
        st.session_state.ll_stats = graph_stats(bundle)
        st.session_state.ll_timeline = timeline_frame(bundle)
    return (st.session_state.ll_analysis, st.session_state.ll_findings,
            st.session_state.ll_stats, st.session_state.ll_timeline)


def _upload_page():
    st.caption("Uploads are processed in this Python session. Files are not sent to a third-party service.")
    st.download_button("Download interaction CSV template", template_csv(), "linklens_interactions_template.csv", mime="text/csv")
    mode = st.radio("Input format", ["Interaction table (CSV or JSON)", "Separate entities + relationships CSVs"], horizontal=True, key="ll_input_mode")
    if mode == "Interaction table (CSV or JSON)":
        upload = st.file_uploader("Choose an interaction file", type=["csv", "json"], key="ll_interaction_file")
        if upload is None:
            st.info("Upload a CSV with source and target columns, or a JSON object/list describing relationships.")
            st.code("source,target,relationship,date,weight\nA,B,call,2025-01-02,1\nB,C,payment,2025-01-05,2", language="csv")
            return
        if upload.name.lower().endswith(".json"):
            if st.button("Validate and load JSON", type="primary"):
                try:
                    _set_bundle(bundle_from_json(upload.getvalue(), upload.name))
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            return
        try:
            frame = read_table(upload)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.caption(f"{len(frame):,} rows · {len(frame.columns)} columns · {upload.name}")
        st.dataframe(frame.head(12), use_container_width=True, hide_index=True)
        columns = list(frame.columns)
        opt = [None, *columns]
        fmt = lambda val: "Not provided" if val is None else str(val)
        def default(candidates, fallback):
            name = auto_col(frame, candidates, fallback)
            return columns.index(name)
        with st.form("ll_interaction_columns"):
            left, right = st.columns(2)
            source = left.selectbox("Source entity ID", columns, index=default(("source","from","caller","sender","entity_a"),0))
            target = right.selectbox("Target entity ID", columns, index=default(("target","to","receiver","recipient","entity_b"),min(1,len(columns)-1)))
            relationship = st.selectbox("Relationship type", opt, index=opt.index(_maybe_col(frame, ("relationship", "rel_type", "relationship_type", "type"))), format_func=fmt)
            date_col = st.selectbox("Date / timestamp", opt, index=opt.index(_maybe_col(frame, ("date", "timestamp", "datetime", "time"))), format_func=fmt)
            weight = st.selectbox("Weight / amount", opt, index=opt.index(_maybe_col(frame, ("weight", "strength", "amount", "count"))), format_func=fmt)
            source_name = st.selectbox("Source display name (optional)", opt, index=0, format_func=fmt)
            target_name = st.selectbox("Target display name (optional)", opt, index=0, format_func=fmt)
            submitted = st.form_submit_button("Load network", type="primary")
        if submitted:
            try:
                _set_bundle(build_from_interactions(frame, source, target, relationship, date_col, weight, source_name, target_name, upload.name))
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        return

    st.write("Use an entity table with stable IDs and a relationship table containing source and target IDs.")
    a, b = st.columns(2)
    with a:
        node_file = st.file_uploader("Entities CSV", type=["csv"], key="ll_entities_file")
    with b:
        edge_file = st.file_uploader("Relationships CSV", type=["csv"], key="ll_relationships_file")
    if node_file is None or edge_file is None:
        st.info("Choose both CSV files to map columns.")
        return
    try:
        nodes, edges = read_table(node_file), read_table(edge_file)
    except ValueError as exc:
        st.error(str(exc))
        return
    a, b = st.columns(2)
    a.dataframe(nodes.head(8), hide_index=True, use_container_width=True)
    b.dataframe(edges.head(8), hide_index=True, use_container_width=True)
    ncols, ecols = list(nodes.columns), list(edges.columns)
    nopt, eopt = [None, *ncols], [None, *ecols]
    fmt = lambda val: "Not provided" if val is None else str(val)
    with st.form("ll_entity_edge_columns"):
        nid = st.selectbox("Entity ID column", ncols, index=ncols.index(auto_col(nodes,("id","entity_id","node_id","identifier"),0)))
        nname = st.selectbox("Entity name column", nopt, index=0, format_func=fmt)
        ntype = st.selectbox("Entity type column", nopt, index=nopt.index(_maybe_col(nodes, ("entity_type", "type", "kind", "category"))), format_func=fmt)
        left, right = st.columns(2)
        es = left.selectbox("Relationship source column", ecols, index=ecols.index(auto_col(edges,("source","from","source_id","u","entity_a"),0)))
        et = right.selectbox("Relationship target column", ecols, index=ecols.index(auto_col(edges, ("target", "to", "target_id", "v", "entity_b"), min(1, len(ecols) - 1))))
        er = st.selectbox("Relationship type column", eopt, index=eopt.index(_maybe_col(edges, ("relationship", "rel_type", "relationship_type", "type"))), format_func=fmt)
        ed = st.selectbox("Date / timestamp column", eopt, index=eopt.index(_maybe_col(edges, ("date", "timestamp", "datetime", "time"))), format_func=fmt)
        ew = st.selectbox("Weight / amount column", eopt, index=eopt.index(_maybe_col(edges, ("weight", "strength", "amount", "count"))), format_func=fmt)
        submitted = st.form_submit_button("Load network", type="primary")
    if submitted:
        try:
            _set_bundle(build_from_nodes_edges(nodes, edges, nid, es, et, nname, ntype, er, ed, ew, f"{node_file.name} + {edge_file.name}"))
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def _pdf(report):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        text = html.unescape(re.sub(r"<[^>]+>", " ", report))
        text = re.sub(r"\s+", " ", text)
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=17*mm, leftMargin=17*mm, topMargin=17*mm, bottomMargin=17*mm)
        styles = getSampleStyleSheet()
        doc.build([Paragraph("LinkLens — Network Analysis Report", styles["Title"]), Spacer(1, 12), Paragraph(xml_escape.escape(text), styles["BodyText"])])
        return buf.getvalue()
    except Exception:
        return None


def render():
    st.set_page_config(page_title="LinkLens · Network Intelligence", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    _init()
    with st.sidebar:
        st.markdown("<div class='ll-eyebrow'>◈ LINKLENS</div><h3 style='margin-top:4px'>Network intelligence</h3>", unsafe_allow_html=True)
        st.caption("Local-first · CPU-only · No paid API")
        st.divider()
        page = st.radio("Workspace", PAGES, index=PAGES.index(st.session_state.ll_page), key="ll_nav")
        st.session_state.ll_page = page
        st.divider()
        st.markdown("**Current case**")
        st.caption(st.session_state.ll_bundle.source_label)
        if st.button("Reset to sample case", use_container_width=True):
            _set_bundle(sample_case())
            st.rerun()
        st.caption("Analysis runs locally. Uploaded records are not transmitted to a service.")

    bundle = st.session_state.ll_bundle
    graph = bundle.graph
    analysis, findings, stats, timeline = _derived(bundle)
    sample = "fictional" in bundle.source_label.lower()
    st.markdown(
        "<div class='ll-hero'><div class='ll-eyebrow'>NETWORK INTELLIGENCE WORKSPACE</div>"
        "<h1>See the connections behind the data.</h1>"
        "<p>Explore relationships, find entities that connect groups, and surface patterns that deserve a closer look.</p>"
        f"<span class='ll-tag'>● Local analysis</span><span class='ll-tag'>{'Fictional sample loaded' if sample else 'Uploaded data in this session'}</span></div>",
        unsafe_allow_html=True,
    )

    if page == "Overview":
        columns = st.columns(4)
        for col, item in zip(columns, [
            ("Entities", stats["entities"], "Distinct entities represented"),
            ("Relationships", stats["relationships"], "Recorded links in this dataset"),
            ("Connected components", stats["components"], "Separate connected portions of the graph"),
            ("Review signals", len(findings), "Heuristics to inspect, not accusations"),
        ]):
            with col:
                _kpi(*item)
        left, right = st.columns([1.45,1], gap="large")
        with left:
            _section("Network at a glance", "Lines represent recorded relationships; this layout is not geography.")
            st.plotly_chart(graph_figure(bundle, analysis), use_container_width=True, config={"displaylogo":False,"scrollZoom":True})
            st.caption("Bridge entities can be useful starting points. Confirm patterns against source records.")
        with right:
            _section("Where to start", "A blended structural review score helps prioritize manual review.")
            st.dataframe(analysis["metrics"][["name","type","direct_links","bridge_links","review_priority"]].head(8).rename(columns={"name":"Entity","type":"Type","direct_links":"Direct links","bridge_links":"Cross-group links","review_priority":"Review priority / 100"}), hide_index=True, use_container_width=True)
            if findings:
                _section("Signals to review", "Automatically surfaced patterns.")
                for f in findings[:3]:
                    st.markdown(f"**{f['severity']} · {f['title']}**  \n{f['evidence']}")
            st.caption("Priority is not a probability of wrongdoing.")

    elif page == "Upload & Map Columns":
        _upload_page()

    elif page == "Network Explorer":
        st.caption("Filter the network, choose an entity and inspect the records behind its direct links.")
        types = sorted({_kind(graph,n) for n in graph})
        rels = sorted({_rel(a) for _,_,a in graph.edges(data=True)})
        c1,c2,c3 = st.columns([1.1,1.4,1])
        selected_types = c1.multiselect("Entity types", types, default=types)
        selected_rels = c2.multiselect("Relationship types", rels, default=rels)
        hops = c3.slider("Focus radius", 0, 2, 1)
        node_ids = list(graph.nodes)
        default = st.session_state.ll_selected if st.session_state.ll_selected in node_ids else node_ids[0]
        selected = st.selectbox("Inspect entity", node_ids, index=node_ids.index(default), format_func=lambda n:f"{_name(graph,n)} · {n}")
        st.session_state.ll_selected = selected
        score = float(analysis["metrics"].set_index("id").loc[str(selected),"review_priority"])
        st.markdown(f"**{html.escape(_name(graph,selected))}** · ID: {html.escape(str(selected))} · {_kind(graph,selected).title()} · {graph.degree(selected)} links · Priority {score:.1f}/100")
        st.plotly_chart(graph_figure(bundle,analysis,selected,selected_types,selected_rels,hops), use_container_width=True, config={"displaylogo":False,"scrollZoom":True})
        rows = [{"Entity":_name(graph,n),"ID":str(n),"Type":_kind(graph,n).title(),"Relationship":_rel(graph[selected][n]),"Weight":graph[selected][n].get("weight",1),"Date":graph[selected][n].get("date","")} for n in graph.neighbors(selected)]
        _section("Direct relationships","Underlying edges connected to the selected entity.")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True) if rows else st.info("No direct relationships for this entity.")

    elif page == "Key Players":
        metric = st.selectbox("Rank by", ["Overall review priority","Most connected","Best bridge between groups","Most influential"])
        keys = {"Overall review priority":"review_priority","Most connected":"direct_links","Best bridge between groups":"bridge_score","Most influential":"influence_score"}
        k = keys[metric]
        frame = analysis["metrics"].sort_values([k,"name"],ascending=[False,True]).head(20).copy()
        frame.insert(0,"Rank",range(1,len(frame)+1))
        frame = frame.rename(columns={"name":"Entity","type":"Type","direct_links":"Direct links","bridge_links":"Cross-group links","most_connected_score":"Connection score","bridge_score":"Bridge score","influence_score":"Influence score","review_priority":"Review priority / 100"})
        st.dataframe(frame[["Rank","Entity","Type","Direct links","Cross-group links","Connection score","Bridge score","Influence score","Review priority / 100"]],hide_index=True,use_container_width=True)
        why = {
            "Overall review priority":"A normalized blend of connection count, bridge position and influence; it is a triage aid only.",
            "Most connected":"Counts direct links. A hub is not necessarily suspicious.",
            "Best bridge between groups":"Highlights network positions spanning different detected communities.",
            "Most influential":"Accounts for whether an entity connects to other well-connected entities.",
        }
        st.info(why[metric])
        st.caption("Review the original relationships and alternative explanations before interpreting a ranking.")

    elif page == "Groups & Communities":
        groups = pd.DataFrame(analysis["communities"])
        if groups.empty:
            st.info("No groups were detected.")
        else:
            chart = px.bar(groups,x="name",y="size",color="dominant_type",hover_data=["leader","density"],title="Detected groups · entities per group",labels={"name":"Group","size":"Entities","dominant_type":"Common type"})
            chart.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(chart,use_container_width=True)
            st.caption("Groups summarize connection structure; they do not establish formal organization.")
            cols = st.columns(3)
            for i,row in groups.iterrows():
                with cols[i%3]:
                    with st.container(border=True):
                        st.markdown(f"### {row['name']}")
                        st.metric("Entities",int(row["size"]))
                        st.write(f"**Most connected:** {row['leader']}")
                        st.write(f"**Common type:** {row['dominant_type']}")
                        st.write(f"**Density:** {row['density']:.2f}")
            st.dataframe(groups[["name","size","leader","dominant_type","density"]].rename(columns={"name":"Group","size":"Entities","leader":"Most connected entity","dominant_type":"Common type","density":"Density"}),hide_index=True,use_container_width=True)

    elif page == "Timeline":
        if timeline.empty:
            st.info("No recognizable dates found. Map a date/timestamp column during upload.")
        else:
            chart = px.area(timeline,x="Date",y="Interactions",markers=True,title="Recorded interactions over time")
            chart.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(chart,use_container_width=True)
            dates = pd.to_datetime(timeline["Date"])
            start,end = dates.min().date(),dates.max().date()
            window = st.date_input("Activity window",value=(start,end),min_value=start,max_value=end)
            if isinstance(window,(tuple,list)) and len(window)==2:
                rows=[]
                for a,b,d in graph.edges(data=True):
                    dt=pd.to_datetime(d.get("date"),errors="coerce")
                    if not pd.isna(dt) and window[0]<=dt.date()<=window[1]:
                        rows.append({"Date":dt.strftime("%Y-%m-%d"),"Entity A":_name(graph,a),"Entity B":_name(graph,b),"Relationship":_rel(d)})
                st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
                st.caption(f"{len(rows)} relationship(s) fall in this period.")
            st.caption("A peak can represent an event, a batch import or differences in record collection.")

    elif page == "Suspicious Patterns":
        st.warning("Heuristic review signals only. Shared resources, bridges and dense circles can all have legitimate explanations.")
        if findings:
            for f in findings:
                with st.container(border=True):
                    st.markdown(f"**{f['severity'].upper()} · {f['title']}**")
                    st.write(f["evidence"])
                    st.write("**Why review:** "+f["why"])
                    st.write("**Suggested next step:** "+f["next"])
        else:
            st.success("No patterns were raised by the current rules. This does not prove the network is risk-free.")
        _section("Candidate missing links","Pairs that share neighbors but have no direct recorded edge.")
        hidden = likely_hidden_links(bundle)
        if hidden.empty:
            st.info("No candidates found from shared neighbors.")
        else:
            st.dataframe(hidden.rename(columns={"Structural confidence":"Shared-neighbor overlap (%)"}),hide_index=True,use_container_width=True)

    elif page == "Case Report":
        st.caption("A portable summary of the loaded network and the signals suggested for review.")
        c1,c2,c3=st.columns(3)
        c1.metric("Entities",stats["entities"]);c2.metric("Relationships",stats["relationships"]);c3.metric("Signals",len(findings))
        st.markdown("### Summary")
        st.write(f"The graph contains {stats['entities']} entities and {stats['relationships']} relationships across {len(analysis['communities'])} detected groups. Rankings support manual triage; they do not establish criminality or guilt.")
        st.markdown("### Suggested next steps")
        st.markdown("1. Validate source provenance and completeness.\n2. Review the underlying edges for top-ranked entities.\n3. Compare timestamps and innocent alternatives.\n4. Record verified facts separately from automated signals.")
        report=report_html(bundle,analysis,findings)
        st.download_button("Download HTML report",report.encode("utf-8"),file_name="linklens_case_report.html",mime="text/html",type="primary")
        pdf=_pdf(report)
        if pdf:
            st.download_button("Download PDF report",pdf,file_name="linklens_case_report.pdf",mime="application/pdf")
        else:
            st.caption("PDF generation is unavailable in this environment; HTML export remains available.")

    else:
        glossary = {
            "Entity":"A record representing a person, organization, account, phone, location, vehicle or event.",
            "Relationship":"A recorded link between two entities, such as a call, payment or shared identifier.",
            "Network / graph":"A set of entities and the relationships connecting them.",
            "Direct links":"The number of relationships directly connected to an entity.",
            "Bridge":"An entity connecting otherwise separate groups in the current graph.",
            "Community / group":"A cluster with relatively dense internal connections.",
            "Density":"How many possible links in a group are present; 1 means all pairs are linked.",
            "Betweenness":"How often an entity sits on shortest paths between other entities.",
            "Influence":"A measure that accounts for connections to well-connected neighbors.",
            "Review priority":"A normalized structural ranking for manual review; not a guilt score or probability.",
            "Link prediction":"A structural hypothesis for a missing relationship based on shared neighbors.",
            "Timeline spike":"A date with a concentration of records, which may also reflect a batch import.",
            "False positive":"A signal that meets a rule but has an innocent explanation.",
            "CSV mapping":"Choosing the columns that contain IDs, dates, weights and relationship types.",
        }
        for term,definition in glossary.items():
            st.markdown(f"**{term}**  \n{definition}")
        st.info("Use LinkLens to organize and explore data, not to make autonomous judgments about people. Verify records and consider innocent explanations.")

    for warning in bundle.warnings:
        st.warning(warning)
    st.divider()
    st.caption("LinkLens · Local-first network exploration · Structural signals are not legal evidence.")


def main():
    render()


if __name__ == "__main__":
    main()
