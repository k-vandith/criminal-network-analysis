"""CRIMENET workspace: rail navigation, map, inspector, cases. No tab dashboard."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.services.case_store import CaseStore

NAV = [
    "Overview",
    "Network",
    "Investigate",
    "Entities",
    "Signals",
    "Timeline",
    "Cases",
    "Reports",
    "Settings",
]


def _init_state() -> None:
    st.session_state.setdefault("page", "Overview")
    st.session_state.setdefault("selected", None)
    st.session_state.setdefault("path_nodes", [])
    st.session_state.setdefault("focus_nodes", None)
    st.session_state.setdefault("active_case", "OPERATION NIGHTFALL")


def command_bar(graph) -> str:
    st.markdown(
        f"<div class='topbar'><div class='brand'>CRIMENET</div>"
        f"<div class='casechip'>CASE · {st.session_state.active_case}</div>"
        f"<div class='live'>● LOCAL · OFFLINE</div></div>",
        unsafe_allow_html=True,
    )
    q = st.text_input(
        "Command",
        placeholder="Search entities, IDs, types, relationship types, communities",
        label_visibility="collapsed",
        key="command_q",
    )
    if q:
        hits = graph.search_entities(q)
        rel_hits = []
        ql = q.lower()
        for u, v, d in graph.G.edges(data=True):
            if ql in str(d.get("rel_type", "")).lower():
                rel_hits.append((u, v, d.get("rel_type")))
        communities = graph.community_detection()
        comm_hits = [n for n, c in communities.items() if ql == str(c)]
        with st.container():
            if hits:
                choice = st.selectbox(
                    "Entity matches",
                    [f"{e.name} · {e.id} · {e.entity_type}" for e in hits[:12]],
                    key="cmd_hit",
                )
                if st.button("Open entity", key="open_hit"):
                    st.session_state.selected = choice.rsplit(" · ", 2)[-2]
                    st.session_state.page = "Network"
                    st.rerun()
            if rel_hits:
                st.caption(f"{len(rel_hits)} relationship matches · {', '.join(sorted({r[2] for r in rel_hits}))}")
            if comm_hits:
                st.caption(f"Community {q}: {len(comm_hits)} entities")
    return q or ""


def _priority_color(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    if score >= 0.5:
        return "ELEVATED"
    if score >= 0.25:
        return "MODERATE"
    return "LOW"


@lru_cache(maxsize=32)
def _layout(nodes: tuple[str, ...], edges: tuple[tuple[str, str, float], ...]) -> dict[str, tuple[float, float]]:
    """Spring layout is the expensive step. Cache it for a fixed node/edge set."""
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_weighted_edges_from(edges)
    pos = nx.spring_layout(g, seed=42, weight="weight")
    return {n: (float(p[0]), float(p[1])) for n, p in pos.items()}


def figure(graph, nodes: list[str], *, labels: bool, mode: str, path_nodes: list[str]) -> go.Figure:
    if not nodes:
        return go.Figure()
    sub = graph.G.subgraph(nodes)
    edge_key = tuple(sorted((u, v, float(d.get("weight", 1.0))) for u, v, d in sub.edges(data=True)))
    pos = _layout(tuple(sorted(nodes)), edge_key)
    communities = graph.community_detection()
    path_set = set(path_nodes or [])
    path_edges = set()
    for a, b in zip(path_nodes, path_nodes[1:]):
        path_edges.add(tuple(sorted((a, b))))

    edge_x, edge_y, hi_x, hi_y = [], [], [], []
    for u, v in sub.edges:
        x0, y0, x1, y1 = pos[u][0], pos[u][1], pos[v][0], pos[v][1]
        if tuple(sorted((u, v))) in path_edges:
            hi_x += [x0, x1, None]
            hi_y += [y0, y1, None]
        else:
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

    traces = [
        go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color="rgba(90,110,140,.45)"), hoverinfo="none"),
        go.Scatter(x=hi_x, y=hi_y, mode="lines", line=dict(width=3, color="#7eb6ff"), hoverinfo="none"),
    ]
    xs, ys, texts, colors, sizes, names = [], [], [], [], [], []
    palette = ["#7eb6ff", "#6fbfa0", "#e2b15a", "#e06b75", "#b79bff", "#8fd0d8", "#d0d4dc"]
    selected = st.session_state.get("selected")
    for nid in sub.nodes:
        ent = graph.entities.get(nid)
        risk = float(ent.risk_score if ent else 0)
        name = ent.name if ent else str(nid)
        kind = ent.entity_type if ent else "unknown"
        degree = graph.G.degree(nid)
        if mode == "Community":
            color = palette[communities.get(nid, 0) % len(palette)]
        elif mode == "Type":
            color = palette[hash(kind) % len(palette)]
        else:
            color = risk
        xs.append(pos[nid][0])
        ys.append(pos[nid][1])
        names.append(name if labels else "")
        texts.append(f"<b>{name}</b><br>{kind} · {nid}<br>Analytical risk {risk:.2f}<br>{degree} direct links")
        sizes.append(16 + 22 * risk + min(degree, 8) + (10 if nid == selected or nid in path_set else 0))
        colors.append(color)
    marker = dict(size=sizes, line=dict(width=1, color="#d5deea"))
    if mode == "Risk":
        marker.update(color=colors, colorscale="YlOrRd", cmin=0, cmax=1, showscale=True, colorbar=dict(title="Risk", thickness=10))
    else:
        marker.update(color=colors, showscale=False)
    traces.append(
        go.Scatter(
            x=xs, y=ys, mode="markers+text" if labels else "markers", text=names,
            textposition="top center", textfont=dict(size=10, color="#c5d0de"),
            hovertext=texts, hoverinfo="text",
            customdata=list(sub.nodes),
            marker=marker,
        )
    )
    fig = go.Figure(traces)
    fig.update_layout(
        height=560, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=4, r=4, t=4, b=4), showlegend=False,
        hoverlabel=dict(bgcolor="#121820", font_size=12),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig


def render_inspector(graph) -> None:
    st.markdown("<div class='kicker'>Entity intelligence</div>", unsafe_allow_html=True)
    options = [f"{e.name} · {eid}" for eid, e in graph.entities.items()]
    current = st.session_state.get("selected")
    index = 0
    if current:
        for i, opt in enumerate(options):
            if opt.endswith(f" · {current}"):
                index = i
                break
    picked = st.selectbox("Entity", options, index=index, label_visibility="collapsed", key="inspector_pick")
    eid = picked.rsplit(" · ", 1)[-1]
    st.session_state.selected = eid
    profile = graph.entity_profile(eid)
    if not profile:
        st.caption("No profile.")
        return
    score = float(profile["risk_score"])
    st.markdown(f"<div class='h'>{profile['name']}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='badge'>{profile['entity_type'].upper()}</span>"
        f"<span class='badge'>{profile['id']}</span>"
        f"<span class='badge'>C{profile['community']}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='panel'><div class='kicker'>Analytical priority signal</div>"
        f"<div class='h'>{int(round(score * 100))} / 100 · {_priority_color(score)}</div>"
        f"<div class='muted'>Heuristic review score. Not a finding of guilt.</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='kicker'>Why surfaced</div>", unsafe_allow_html=True)
    for reason in profile["reasons"] or ["No special signal."]:
        st.markdown(f"<div class='sig'>{reason}</div>", unsafe_allow_html=True)
    c = profile["centrality"]
    rows = [
        ("Degree", c.get("degree_centrality", 0)),
        ("Betweenness", c.get("betweenness_centrality", 0)),
        ("Closeness", c.get("closeness_centrality", 0)),
        ("Eigenvector", c.get("eigenvector_centrality", 0)),
    ]
    st.markdown("<div class='kicker'>Centrality</div>", unsafe_allow_html=True)
    for label, value in rows:
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;font-size:.82rem'>"
            f"<span>{label}</span><span>{float(value or 0):.3f}</span></div>",
            unsafe_allow_html=True,
        )
    ego = graph.ego_network(eid)
    st.markdown(
        f"<div class='muted' style='margin-top:8px'>{len(profile['neighbors'])} direct links · "
        f"{ego['communities_touched']} communities touched</div>",
        unsafe_allow_html=True,
    )
    if profile["attributes"]:
        st.markdown("<div class='kicker'>Attributes</div>", unsafe_allow_html=True)
        for k, v in profile["attributes"].items():
            st.markdown(f"<div class='muted'>{k}: {v}</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("2-hop", width="stretch"):
        st.session_state.focus_nodes = graph.neighborhood(eid, 2)
        st.session_state.page = "Network"
        st.rerun()
    if c2.button("Find path", width="stretch"):
        st.session_state.page = "Investigate"
        st.rerun()
    if st.button("Pin to case", width="stretch"):
        st.session_state.setdefault("pinned", [])
        if eid not in st.session_state.pinned:
            st.session_state.pinned.append(eid)
        st.success(f"Pinned {profile['name']}")


def _visible_nodes(graph, query: str) -> list[str]:
    focus = st.session_state.get("focus_nodes")
    base = focus if focus else list(graph.G.nodes)
    if not query:
        return base
    ql = query.lower()
    return [
        n for n in base
        if ql in graph.entities[n].name.lower() or ql in n.lower() or ql in graph.entities[n].entity_type.lower()
    ]


def render_map(graph, nodes: list[str]) -> None:
    controls = st.columns(8)
    labels = controls[0].toggle("Labels", value=len(nodes) <= 24)
    mode = controls[1].selectbox("Color", ["Risk", "Community", "Type"], label_visibility="collapsed")
    if controls[2].button("Fit"):
        st.session_state.focus_nodes = None
    if controls[3].button("Reset"):
        st.session_state.focus_nodes = None
        st.session_state.path_nodes = []
    hops = controls[4].selectbox("Expand", ["1-hop", "2-hop", "3-hop"], index=1, label_visibility="collapsed")
    if controls[5].button("Focus") and st.session_state.get("selected"):
        n = int(hops[0])
        st.session_state.focus_nodes = graph.neighborhood(st.session_state.selected, n)
        st.rerun()
    hide_iso = controls[6].toggle("Hide isolates", value=False)
    if hide_iso:
        nodes = [n for n in nodes if graph.G.degree(n) > 0]
    st.caption(f"Network map · {len(nodes)} entities in view · seed 42 layout")
    fig = figure(graph, nodes, labels=labels, mode=mode, path_nodes=st.session_state.get("path_nodes") or [])
    try:
        event = st.plotly_chart(fig, width="stretch", config={"displaylogo": False}, on_select="rerun", key="map")
        points = []
        if event and getattr(event, "selection", None):
            points = event.selection.get("points", [])
        if points and points[0].get("customdata"):
            st.session_state.selected = points[0]["customdata"]
    except TypeError:
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


def screen_overview(graph, nodes: list[str]) -> None:
    health = graph.network_health()
    high = graph.bridge_entities(50)
    cross = int((high["cross_community_links"] > 0).sum()) if not high.empty else 0
    anomalies = graph.anomaly_detection(50)
    anom_n = int((anomalies["anomaly_score"] >= 1).sum()) if not anomalies.empty else 0
    flags = graph.suspicious_relationships()
    st.markdown(
        f"<div class='panel'><div class='kicker'>Network health</div><div class='statrow'>"
        f"<div class='stat'><b>{health['entities']}</b><span>Entities</span></div>"
        f"<div class='stat'><b>{health['relationships']}</b><span>Relationships</span></div>"
        f"<div class='stat'><b>{health['communities']}</b><span>Communities</span></div>"
        f"<div class='stat'><b>{health['density']}</b><span>Density</span></div>"
        f"<div class='stat'><b>{health['components']}</b><span>Components</span></div>"
        f"<div class='stat'><b>{health['articulation_points']}</b><span>Cut vertices</span></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.7, 1])
    with left:
        st.markdown("<div class='kicker'>Network map</div>", unsafe_allow_html=True)
        render_map(graph, nodes)
    with right:
        st.markdown("<div class='kicker'>Top analytical priority</div>", unsafe_allow_html=True)
        rank = graph.key_player_explanations(6)
        for _, row in rank.iterrows():
            tone = "danger" if row["risk_score"] >= 0.75 else "warn"
            st.markdown(
                f"<div class='sig {tone}'><b>{int(row['rank']):02d}  {row['name']}</b>"
                f"<div class='muted'>{row['entity_type']} · priority {row['kingpin_score']:.2f}</div>"
                f"<div class='muted'>{row['why_flagged']}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button(f"Inspect {row['id']}", key=f"ov_{row['id']}"):
                st.session_state.selected = row["id"]
                st.session_state.page = "Network"
                st.rerun()
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='panel'><div class='kicker'>Bridge candidates</div><div class='h'>{cross}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='panel'><div class='kicker'>Anomaly candidates</div><div class='h'>{anom_n}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='panel'><div class='kicker'>Cross-community links</div><div class='h'>{sum(1 for f in flags if f.get('cross_community'))}</div></div>", unsafe_allow_html=True)


def screen_network(graph, nodes: list[str]) -> None:
    left, right = st.columns([1.65, 0.85])
    with left:
        render_map(graph, nodes)
        with st.expander("Physics layout (secondary)"):
            html = graph.to_pyvis_html(Path("data/sample/network_interactive.html"))
            components.html(html, height=480, scrolling=True)
    with right:
        render_inspector(graph)


def screen_investigate(graph) -> None:
    ids = list(graph.entities)
    labels = [f"{graph.entities[i].name} · {i}" for i in ids]
    a, b, mode = st.columns([1, 1, 1])
    src = a.selectbox("Source", labels, key="path_src")
    dst = b.selectbox("Target", labels, index=min(1, len(labels) - 1), key="path_dst")
    kind = mode.selectbox("Path", ["Shortest", "Weighted"])
    sid, tid = src.rsplit(" · ", 1)[-1], dst.rsplit(" · ", 1)[-1]
    if sid == tid:
        st.info("Choose two different entities.")
        return
    df = graph.shortest_investigation_path(sid, tid) if kind == "Shortest" else graph.weighted_investigation_path(sid, tid)
    if df.empty:
        st.warning("No path. The entities are disconnected.")
        st.session_state.path_nodes = []
        return
    st.session_state.path_nodes = df["id"].tolist()
    hops = len(df) - 1
    communities = graph.community_detection()
    transitions = sum(
        1 for i in range(1, len(df))
        if communities.get(df.iloc[i - 1]["id"]) != communities.get(df.iloc[i]["id"])
    )
    st.markdown(
        f"<div class='panel'><div class='kicker'>Relationship chain</div>"
        f"<div class='h'>{hops} hop(s) · {transitions} community transition(s)</div></div>",
        unsafe_allow_html=True,
    )
    for i, row in df.iterrows():
        if i:
            st.markdown(f"<div class='muted'>│ {row['relationship_from_previous']}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sig'><b>{row['name']}</b> <span class='badge'>{row['entity_type']}</span>"
            f"<span class='badge'>{row['id']}</span></div>",
            unsafe_allow_html=True,
        )
    render_map(graph, list(graph.G.nodes))


def screen_entities(graph) -> None:
    st.markdown("<div class='kicker'>Communities</div>", unsafe_allow_html=True)
    summary = graph.community_summary()
    cols = st.columns(min(3, max(1, len(summary))))
    for i, row in summary.iterrows():
        with cols[i % len(cols)]:
            st.markdown(
                f"<div class='panel'><div class='kicker'>Community {int(row['community']):02d}</div>"
                f"<div class='h'>{int(row['entities'])} entities</div>"
                f"<div class='muted'>{int(row['relationships'])} relationships · density {row['density']}</div>"
                f"<div class='muted'>Dominant {row['dominant_type']}</div>"
                f"<div class='muted'>Core {row['core_entity']}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button("Explore", key=f"comm_{row['community']}"):
                mapping = graph.community_detection()
                st.session_state.focus_nodes = [n for n, c in mapping.items() if c == row["community"]]
                st.session_state.page = "Network"
                st.rerun()
    st.markdown("<div class='kicker'>Priority register</div>", unsafe_allow_html=True)
    rank = graph.key_player_explanations(15)
    st.dataframe(
        rank,
        hide_index=True,
        width="stretch",
        column_config={"kingpin_score": st.column_config.NumberColumn("Analytical priority", format="%.3f")},
    )


def screen_signals(graph) -> None:
    bridges = graph.bridge_entities(8)
    anomalies = graph.anomaly_detection(8)
    flags = graph.suspicious_relationships()[:8]
    links = graph.link_prediction(6)
    left, right = st.columns(2)
    with left:
        st.markdown("<div class='kicker'>Bridge candidates</div>", unsafe_allow_html=True)
        for _, row in bridges.iterrows():
            if row["cross_community_links"] <= 0:
                continue
            st.markdown(
                f"<div class='sig warn'><b>{row['name']}</b><div class='muted'>Connects outside community {row['community']}.</div>"
                f"<div class='muted'>Cross links {int(row['cross_community_links'])} · ratio {row['bridge_ratio']}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button("Inspect", key=f"br_{row['id']}"):
                st.session_state.selected = row["id"]
                st.session_state.page = "Network"
                st.rerun()
        st.markdown("<div class='kicker'>Suspicious relationships</div>", unsafe_allow_html=True)
        for flag in flags:
            st.markdown(
                f"<div class='sig'><b>{flag['source']} → {flag['target']}</b>"
                f"<div class='muted'>{flag['rel_type']} · weight {flag['weight']} · {flag['reason']}</div></div>",
                unsafe_allow_html=True,
            )
    with right:
        st.markdown("<div class='kicker'>Anomaly candidates</div>", unsafe_allow_html=True)
        for _, row in anomalies.head(6).iterrows():
            st.markdown(
                f"<div class='sig danger'><b>{row['name']}</b><div class='muted'>{row['reason']}</div>"
                f"<div class='muted'>score {row['anomaly_score']} · degree {row['degree']} · weighted {row['weighted_degree']}</div></div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div class='kicker'>Potential links</div>", unsafe_allow_html=True)
        if links.empty:
            st.caption("No unlinked pairs scored.")
        else:
            for _, row in links.iterrows():
                st.markdown(
                    f"<div class='sig'><b>{row['source_name']} · {row['target_name']}</b>"
                    f"<div class='muted'>score {row['score']} · {row['method']}</div></div>",
                    unsafe_allow_html=True,
                )


def screen_timeline(graph) -> None:
    timeline = graph.timeline_events()
    if timeline.empty:
        st.info("No event entities in this dataset.")
        return
    st.markdown("<div class='kicker'>Event timeline</div>", unsafe_allow_html=True)
    for _, row in timeline.iterrows():
        st.markdown(
            f"<div class='sig'><div class='kicker'>{row.get('date') or 'undated'}</div>"
            f"<b>{row['name']}</b><div class='muted'>{row.get('description','')}</div>"
            f"<div class='muted'>Location ref {row.get('location') or '—'}</div></div>",
            unsafe_allow_html=True,
        )
        if st.button(f"Focus {row['id']}", key=f"tl_{row['id']}"):
            st.session_state.selected = row["id"]
            st.session_state.focus_nodes = graph.neighborhood(row["id"], 1)
            st.session_state.page = "Network"
            st.rerun()


def screen_cases(graph, store: CaseStore) -> None:
    cases = store.list_cases()
    st.markdown("<div class='kicker'>Case workspace</div>", unsafe_allow_html=True)
    name = st.text_input("Case name", value=st.session_state.active_case)
    desc = st.text_area("Description", height=80, placeholder="What is being reviewed?")
    notes = st.text_area("Notes", height=80)
    pinned = st.session_state.get("pinned", [])
    st.caption("Pinned entities: " + (", ".join(pinned) if pinned else "none"))
    if st.button("Save case locally"):
        saved = store.save_case(
            {
                "name": name,
                "description": desc,
                "notes": notes,
                "entities": pinned,
                "signals": ["bridge candidate", "anomaly candidate"],
                "findings": [],
            }
        )
        st.session_state.active_case = saved["name"]
        st.success(f"Stored {saved['id']} in {store.path}")
    if cases:
        st.markdown("<div class='kicker'>Stored cases</div>", unsafe_allow_html=True)
        for case in cases:
            st.markdown(
                f"<div class='panel'><b>{case.get('name')}</b> <span class='badge'>{case.get('id')}</span>"
                f"<div class='muted'>{case.get('description') or 'No description'}</div>"
                f"<div class='muted'>{len(case.get('entities') or [])} pinned entities</div></div>",
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"case_{case.get('id')}"):
                st.session_state.active_case = case.get("name")
                st.session_state.pinned = list(case.get("entities") or [])
                st.rerun()


def screen_reports(graph, out_dir: Path) -> None:
    st.markdown("<div class='kicker'>Report builder</div>", unsafe_allow_html=True)
    st.caption("Generated locally. Scores are heuristic review signals, not legal evidence.")
    opts = {
        "Executive summary": True,
        "Network overview": True,
        "Priority entities": True,
        "Communities": True,
        "Signals": True,
        "Timeline": True,
        "Methodology": True,
        "Limitations": True,
    }
    chosen = [label for label, default in opts.items() if st.checkbox(label, value=default)]
    c1, c2 = st.columns(2)
    if c1.button("Generate HTML", width="stretch"):
        path = graph.export_html_report(out_dir / "network_intelligence_report.html")
        text = path.read_text(encoding="utf-8")
        banner = "<p>Sections: " + ", ".join(chosen) + "</p>"
        text = text.replace("</h1>", "</h1>" + banner, 1)
        path.write_text(text, encoding="utf-8")
        st.download_button("Download HTML", text, file_name=path.name, width="stretch")
    if c2.button("Generate PDF", width="stretch"):
        path = graph.export_pdf_report(out_dir / "network_intelligence_report.pdf")
        if path.suffix.lower() == ".pdf":
            st.download_button("Download PDF", path.read_bytes(), file_name=path.name, mime="application/pdf")
        else:
            st.warning(f"ReportLab unavailable. Wrote {path.name}")


def screen_settings(graph) -> None:
    health = graph.network_health()
    st.markdown("<div class='notice'>Analytical priority scores are heuristic review signals and are not findings of guilt or legal evidence.</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='panel'><div class='kicker'>Graph</div>"
        f"<div class='muted'>Undirected weighted NetworkX graph. "
        f"Clustering {health['average_clustering']}. Diameter {health['diameter']}.</div>"
        f"<div class='muted'>Betweenness uses edge weight. Eigenvector falls back to NumPy, then zeros.</div></div>",
        unsafe_allow_html=True,
    )
    st.caption("Core analysis does not call external APIs. Keep real case data out of this repository.")


def render(graph, store: CaseStore, out_dir: Path) -> None:
    _init_state()
    with st.sidebar:
        st.markdown("<div class='brand'>CRIMENET</div>", unsafe_allow_html=True)
        st.caption("NETWORK INTELLIGENCE")
        page = st.radio("Section", NAV, index=NAV.index(st.session_state.page), label_visibility="collapsed")
        st.session_state.page = page
        st.divider()
        st.caption("Synthetic demo · offline")
    query = command_bar(graph)
    nodes = _visible_nodes(graph, query)
    if page == "Overview":
        screen_overview(graph, nodes)
    elif page == "Network":
        screen_network(graph, nodes)
    elif page == "Investigate":
        screen_investigate(graph)
    elif page == "Entities":
        screen_entities(graph)
    elif page == "Signals":
        screen_signals(graph)
    elif page == "Timeline":
        screen_timeline(graph)
    elif page == "Cases":
        screen_cases(graph, store)
    elif page == "Reports":
        screen_reports(graph, out_dir)
    else:
        screen_settings(graph)
    st.markdown(
        "<div class='muted' style='margin-top:12px'>Analytical priority scores are heuristic review signals "
        "and are not findings of guilt or legal evidence.</div>",
        unsafe_allow_html=True,
    )
