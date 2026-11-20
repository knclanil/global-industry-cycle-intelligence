"""Global / USA / India: rotation -> sector -> company -> factor graph.

Requires existing rotation_graph_evidence.py and generated *_signals.csv / *_edges.csv.
Sector and factor rotation classes describe the *index*, not the company price.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from rotation_graph_evidence import QUADRANTS, graph_elements

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "data" / "dashboard_cache" / "rotation_graphs"
PALETTE = {"Leading": "#34d399", "Improving": "#60a5fa",
           "Weakening": "#fbbf24", "Lagging": "#fb7185"}
NODE_COLOR = {"sector": "#7dd3fc", "company": "#e5e7eb", "factor": "#c4b5fd"}
BG = "#101827"


@st.cache_data(show_spinner=False, max_entries=48)
def _read_csv(path: str, mtime: int) -> pd.DataFrame:
    try:
        return pd.read_csv(path, keep_default_na=False)
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _load(region: str, period: str, kind: str) -> pd.DataFrame:
    p = STORE / f"{region.lower()}_{period}_{kind}.csv"
    return _read_csv(str(p), p.stat().st_mtime_ns if p.exists() else -1)


def _manifest() -> dict:
    try:
        return json.loads((STORE / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _indexed(nodes, links):
    by_id = {n["id"]: n for n in nodes}
    linked = defaultdict(set)  # index id -> company ids
    company_sources = defaultdict(set)
    for source, target in links:
        if source.startswith("i:") and target.startswith("c:"):
            linked[source].add(target)
            company_sources[target].add(source)
    return by_id, linked, company_sources


def _sorted(nodes):
    order = {q: i for i, q in enumerate(QUADRANTS)}
    return sorted(nodes, key=lambda n: (order.get(n.get("quadrant"), 99),
                                        n.get("label", "").casefold(), n["id"]))


def _choose_visible(nodes, links, selection: str | list[str] | dict, max_companies: int | None,
                    match_mode: str = "Any selected"):
    """Return source nodes and company nodes; preserve every evidenced edge.

    In focused mode, include all other sector/factor sources connected to selected
    companies so that a company's dual sector/factor membership is visible.
    """
    by_id, linked, company_sources = _indexed(nodes, links)
    source_ids = {n["id"] for n in nodes if n["type"] in ("sector", "factor")}
    if isinstance(selection, dict) and selection.get("mode") == "matched":
        company_ids = set(selection.get("companies", ())) & {n["id"] for n in nodes if n["type"] == "company"}
        chosen_sources = set(selection.get("sources", ())) & source_ids
        for company_id in company_ids:
            chosen_sources.update(company_sources[company_id])
    elif selection == "all":
        company_ids = {n["id"] for n in nodes if n["type"] == "company"}
        chosen_sources = source_ids
    elif isinstance(selection, str) and selection.startswith("c:"):
        # Individual-company mode: show its entire evidenced sector/factor network.
        company_ids = {selection} if selection in by_id else set()
        chosen_sources = set(company_sources.get(selection, ()))
    else:
        # Multiple sector/factor selections: union (any) or intersection (all).
        selected_sources = ([selection] if isinstance(selection, str) else list(selection))
        selected_sources = [sid for sid in dict.fromkeys(selected_sources)
                            if sid in source_ids]
        memberships = [set(linked.get(sid, ())) for sid in selected_sources]
        if not memberships:
            company_ids = set()
        elif match_mode == "All selected":
            company_ids = set.intersection(*memberships)
        else:
            company_ids = set.union(*memberships)
        # Always retain selected sector/factor nodes, even if they have no companies.
        chosen_sources = set(selected_sources)
        for company_id in company_ids:
            chosen_sources.update(company_sources[company_id])
    if max_companies is not None and len(company_ids) > max_companies:
        company_ids = set(sorted(company_ids, key=lambda cid: (
            by_id[cid].get("label", "").casefold(), cid))[:max_companies])
        if selection != "all":
            if isinstance(selection, dict):
                chosen_sources = set(selection.get("sources", ()))
            else:
                chosen_sources = (set(selection) if isinstance(selection, list) else
                                  {selection} if selection.startswith("i:") else set())
            for company_id in company_ids:
                chosen_sources.update(company_sources[company_id])
    return (_sorted([by_id[s] for s in chosen_sources if s in by_id and by_id[s]["type"] == "sector"]),
            _sorted([by_id[s] for s in chosen_sources if s in by_id and by_id[s]["type"] == "factor"]),
            sorted([by_id[c] for c in company_ids], key=lambda n: (n.get("label", "").casefold(), n["id"])),
            linked, company_sources)


def _draw(nodes, links, selection: str | list[str] | dict, max_companies: int | None,
          match_mode: str = "Any selected"):
    by_id = {n["id"]: n for n in nodes}
    sectors, factors, companies, members, company_sources = _choose_visible(
        nodes, links, selection, max_companies, match_mode)
    selected_ids = {n["id"] for n in sectors + factors + companies}
    positions = {f"q:{q}": (0., 1 - (i + 0.5) / len(QUADRANTS))
                 for i, q in enumerate(QUADRANTS)}
    for x, group in ((1., sectors), (2.15, companies), (3.3, factors)):
        for i, node in enumerate(group):
            positions[node["id"]] = (x, 1 - (i + .5) / max(1, len(group)))
    fig = go.Figure()

    # Sector path: rotation -> sector -> company.
    # Factor path: rotation -> company -> factor (only when a mapped factor exists).
    # A factor-only company still shows a valid rotation -> company connection.
    for quadrant in QUADRANTS:
        segments = set()
        for source in sectors:
            if source["quadrant"] == quadrant:
                segments.add((f"q:{quadrant}", source["id"]))
                segments.update((source["id"], cid) for cid in members[source["id"]]
                                if cid in selected_ids)
        for factor in factors:
            if factor["quadrant"] == quadrant:
                for cid in members[factor["id"]]:
                    if cid in selected_ids:
                        segments.add((cid, factor["id"]))
                        # Connect rotation directly to a factor-only company;
                        # otherwise the factor's own rotation would be invisible.
                        if not any(by_id[s]["type"] == "sector" and
                                   by_id[s]["quadrant"] == quadrant
                                   for s in company_sources[cid] if s in selected_ids):
                            segments.add((f"q:{quadrant}", cid))
                if not members[factor["id"]].intersection(selected_ids):
                    # Keep unconnected factor signals visible with their rotation.
                    segments.add((f"q:{quadrant}", factor["id"]))
        xs, ys = [], []
        for start, end in sorted(segments):
            if start not in positions or end not in positions:
                continue
            a, b = positions[start], positions[end]
            xs.extend((a[0], b[0], None))
            ys.extend((a[1], b[1], None))
        if xs:
            fig.add_trace(go.Scattergl(x=xs, y=ys, mode="lines",
                                      line=dict(color=PALETTE[quadrant], width=1.2),
                                      opacity=.36, hoverinfo="skip", showlegend=False))

    def add_nodes(group, title, color, size, symbol="circle", display_text=True):
        if not group:
            return
        fig.add_trace(go.Scattergl(
            x=[positions[n["id"]][0] for n in group],
            y=[positions[n["id"]][1] for n in group],
            mode="markers+text" if display_text else "markers",
            marker=dict(size=size, color=color, symbol=symbol),
            text=[n["label"] for n in group],
            textposition="middle left" if title == "Rotations" else "middle right",
            textfont=dict(size=11, color="#e5e7eb"),
            hovertext=[(f"<b>{n.get('name') or n['label']}</b>"
                        + (f"<br>Quadrant: {n['quadrant']}"
                           f"<br>RS: {n.get('rs', 'N/A')}"
                           f"<br>Momentum: {n.get('momentum', 'N/A')}"
                           f"<br>Company memberships: {len(members[n['id']])}"
                           if n["type"] in ("sector", "factor") else "")) for n in group],
            hovertemplate="%{hovertext}<extra></extra>", name=title))

    # With active filters, hide rotation nodes that have no visible connection.
    filtered = isinstance(selection, dict) and selection.get("mode") == "matched"
    displayed_quadrants = ([q for q in QUADRANTS if any(
        n.get("quadrant") == q for n in sectors + factors)] if filtered
        else list(QUADRANTS))
    add_nodes([by_id[f"q:{q}"] for q in displayed_quadrants], "Rotations",
              [PALETTE[q] for q in displayed_quadrants], 19)
    add_nodes(sectors, "Sectors", NODE_COLOR["sector"], 10)
    add_nodes(companies, "Companies", "#a7f3d0" if selection != "all" else NODE_COLOR["company"], 9,
              display_text=len(companies) <= 35)
    add_nodes(factors, "Factors", NODE_COLOR["factor"], 10, symbol="diamond")
    for x, label in ((0, "ROTATIONS"), (1., "SECTORS"),
                     (2.15, "COMPANIES"), (3.3, "FACTORS")):
        fig.add_annotation(x=x, y=1.08, text=f"<b>{label}</b>", showarrow=False,
                           font=dict(size=12, color="#e5edf7"))
    fig.update_layout(
        height=730 if len(companies) <= 80 else min(2400, 730 + 8 * (len(companies)-80)),
        paper_bgcolor=BG, plot_bgcolor=BG,
        margin=dict(l=105, r=100, t=80, b=35),
        xaxis=dict(visible=False, range=[-.4, 3.8], fixedrange=True),
        yaxis=dict(visible=False, range=[-.04, 1.14], fixedrange=True),
        font=dict(color="#e5edf7"), showlegend=True,
        legend=dict(orientation="h", y=-.02, x=0), hovermode="closest")
    st.plotly_chart(fig, use_container_width=True,
                    config={"displaylogo": False, "scrollZoom": False})
    return sectors, companies, factors


def render_graph(region: str):
    if region not in ("Global", "USA", "India"):
        st.error("Unsupported region")
        return
    st.title(f"{region} Rotation Knowledge Graph")
    st.caption("Four rotations → Sector → Company → Factor. "
               "Sectors and factors have their own rotation signals.")
    period = st.selectbox("Lookback", ["1m", "3m", "6m"], index=1,
                          key=f"kg_period_{region}")
    signals, edges = _load(region, period, "signals"), _load(region, period, "edges")
    status = _manifest().get("regions", {}).get(f"{region.lower()}_{period}", {})
    if signals.empty:
        st.warning("No rotation signals. Run Refresh Knowledge Graphs in GitHub Actions.")
        return
    if not (STORE / f"{region.lower()}_{period}_edges.csv").is_file():
        st.error("Membership snapshot missing. Run Refresh Knowledge Graphs in GitHub Actions.")
        return
    if status.get("error"):
        st.warning(f"Latest builder reported: {status['error']}")
    nodes, links = graph_elements(signals, edges)
    by_id, memberships, _ = _indexed(nodes, links)
    cols = st.columns(4)
    for col, quadrant in zip(cols, QUADRANTS):
        indices = sum(n["type"] in ("sector", "factor") and n["quadrant"] == quadrant for n in nodes)
        col.metric(quadrant, indices)
    # All three views share exactly the same four-column renderer.
    view = st.radio(
        "Graph view",
        ["Overview", "Sector / Factor", "Individual Companies"],
        horizontal=True, key=f"kg_view_{region}",
    )
    sources = _sorted([n for n in nodes if n["type"] in ("sector", "factor")])
    companies_all = sorted(
        (n for n in nodes if n["type"] == "company"),
        key=lambda n: (n.get("label", "").casefold(), n["id"]),
    )
    # All three graph views expose the same multi-value filters. Empty filters
    # mean no restriction; selecting values immediately removes unrelated nodes.
    st.caption("Select multiple rotations, sectors, factors, and companies. "
               "Only connected results stay visible; unrelated nodes disappear.")
    with st.expander("Filters · select multiple values", expanded=True):
        col1, col2 = st.columns([1.6, 1])
        with col1:
            rotation_filter = st.multiselect(
                "Rotations (multiple)", list(QUADRANTS), default=[],
                key=f"kg_rotations_{region}",
                placeholder="All rotations")
        with col2:
            match_mode = st.radio(
                "Match selected sector/factor nodes", ["Any selected", "All selected"],
                horizontal=True, key=f"kg_match_{region}")
        sector_options = {n["id"]: f"{n['label']} · {n['quadrant']}" for n in sources
                          if n["type"] == "sector"}
        factor_options = {n["id"]: f"{n['label']} · {n['quadrant']}" for n in sources
                          if n["type"] == "factor"}
        company_options = {n["id"]: f"{n.get('name') or n['label']} · {n['label']}"
                           for n in companies_all}
        left, right = st.columns(2)
        with left:
            selected_sectors = st.multiselect(
                "Sectors (multiple)", list(sector_options),
                format_func=lambda sid: sector_options.get(sid, sid),
                key=f"kg_sectors_{region}")
        with right:
            selected_factors = st.multiselect(
                "Factors (multiple)", list(factor_options),
                format_func=lambda sid: factor_options.get(sid, sid),
                key=f"kg_factors_{region}")
        selected_companies = st.multiselect(
            "Individual companies (multiple)", list(company_options),
            format_func=lambda cid: company_options.get(cid, cid),
            key=f"kg_companies_{region}", placeholder="All companies")

    active = bool(rotation_filter or selected_sectors or selected_factors or selected_companies)
    show_all = st.checkbox("Show all matching companies (dense graph)", value=False,
                           key=f"kg_show_all_{region}")
    max_companies = None if show_all else (60 if view == "Overview" else 100)
    if not active:
        focus = "all"
    else:
        # A rotation is a constraint on sector/factor index signals; it is NOT
        # a derived rotation for the individual company.
        allowed_sources = {n["id"] for n in sources
                           if not rotation_filter or n["quadrant"] in rotation_filter}
        chosen_sources = set(selected_sectors) | set(selected_factors)
        if chosen_sources:
            source_sets = [set(memberships.get(sid, ())) for sid in chosen_sources]
            matched = (set.intersection(*source_sets) if match_mode == "All selected"
                       else set.union(*source_sets))
        else:
            matched = {n["id"] for n in companies_all}
        if rotation_filter:
            rotation_companies = set().union(
                *(memberships.get(sid, set()) for sid in allowed_sources)) if allowed_sources else set()
            matched &= rotation_companies
        if selected_companies:
            matched &= set(selected_companies)
        # Show selected sources even if they lack verified company memberships,
        # but do not display unrelated sectors / factors / companies.
        visible_sources = chosen_sources if chosen_sources else (
            allowed_sources if rotation_filter and not selected_companies else set())
        focus = {"mode": "matched", "companies": matched,
                 "sources": visible_sources}
        if not matched:
            st.info("No verified company memberships match these filters.")
        st.caption(f"{len(matched):,} matching companies · "
                   f"{len(selected_sectors)} selected sectors · "
                   f"{len(selected_factors)} selected factors · "
                   f"{len(selected_companies)} selected companies")
    sectors, companies, factors = _draw(nodes, links, focus, max_companies, match_mode)
    st.caption(f"Visible: {len(sectors)} sectors · {len(companies)} companies · "
               f"{len(factors)} factors. Overall graph: {len(nodes)} nodes / "
               f"{len(links)} relationships. No membership data is discarded.")
    st.info("Rotation labels describe sector/factor index signals, not independent "
            "company price classifications. Factor-only companies connect to their "
            "rotation directly when no same-quadrant sector link exists.")
    with st.expander("All sector & factor signals"):
        st.dataframe(signals, use_container_width=True, hide_index=True)
    with st.expander("All verified company memberships"):
        st.dataframe(edges, use_container_width=True, hide_index=True)
    with st.expander("Unmapped source records"):
        st.dataframe(_load(region, period, "unmapped"), use_container_width=True, hide_index=True)
