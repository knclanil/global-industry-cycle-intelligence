"""Capital membership network: GLOBAL -> COUNTRY -> SECTOR -> COMPANY -> FACTOR.

The GLOBAL root ALSO has its own direct connections to global-scoped sectors,
companies and factors (independent of the country-specific branches).

Uses *verified* cached sector and factor constituents. This is a relationship
network, NOT a measured capital-flow network. Country assignment is only made
when the membership is present in an explicitly country-scoped regional cache.

Drop in as `capital_network.py` at the repository root. The application's
existing `render_capital_network()` route needs no change.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dashboard_cache" / "rotation_graphs"
PERIODS = ("1m", "3m", "6m")
REGIONS = ("USA", "India", "Global")
QUADRANTS = ("Leading", "Improving", "Weakening", "Lagging")
COLORS = {"Leading": "#36d6a2", "Improving": "#6ba9ff",
          "Weakening": "#ffca70", "Lagging": "#fa8297", "Unavailable": "#8f9db3"}
BG = "#111b2b"


@st.cache_data(show_spinner=False, max_entries=40)
def _csv(path: str, stamp: int) -> pd.DataFrame:
    try:
        return pd.read_csv(path, keep_default_na=False, dtype=str)
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _load(region: str, period: str, kind: str, directory: Path = CACHE_DIR) -> pd.DataFrame:
    file = directory / f"{region.lower()}_{period}_{kind}.csv"
    return _csv(str(file), file.stat().st_mtime_ns if file.is_file() else -1)


def _normal(value) -> str:
    return str(value).strip()


def _graph_data(period: str, directory: Path = CACHE_DIR):
    """Build evidence-preserving relationships without guessing geographic origin.

    Returns (nodes, edges, diagnostics). Nodes keyed by unique, typed IDs.
    Global portfolio data branches directly from the GLOBAL root; it is never
    assigned to an invented USA/India country.
    """
    nodes = {"root": {"label": "GLOBAL", "kind": "root", "country": None}}
    edges = set()
    diagnostics = {}

    def put(nid, **properties):
        nodes.setdefault(nid, properties)

    def link(source, target):
        if source in nodes and target in nodes:
            edges.add((source, target))

    for region in REGIONS:
        signals = _load(region, period, "signals", directory)
        memberships = _load(region, period, "edges", directory)
        valid_signals = {"source_id", "kind", "label", "quadrant"}.issubset(signals.columns)
        valid_edges = {"source_id", "kind", "company_key", "Company", "Ticker"}.issubset(memberships.columns)
        diagnostics[region] = {"signals": len(signals), "memberships": len(memberships),
                               "signals_valid": valid_signals, "edges_valid": valid_edges}
        if not valid_signals:
            continue
        # Country branches are explicit ONLY for country-scoped evidence.
        # Global signals and memberships belong directly to the GLOBAL node,
        # rather than being forced into a fictitious country node.
        country_id = None
        if region in ("USA", "India"):
            country_label = {"USA": "United States", "India": "India"}[region]
            country_id = f"country:{region}"
            put(country_id, label=country_label, kind="country", country=region)
            link("root", country_id)

        lookup = {}
        for row in signals.to_dict("records"):
            source_id, kind = _normal(row.get("source_id")), _normal(row.get("kind")).lower()
            quadrant = _normal(row.get("quadrant"))
            if not source_id or kind not in ("sector", "factor") or quadrant not in QUADRANTS:
                continue
            sid = f"{region}:{kind}:{source_id}"
            lookup[(kind, source_id)] = sid
            put(sid, label=_normal(row.get("label")) or source_id, kind=kind,
                country=region, quadrant=quadrant,
                rs=_normal(row.get("relative_strength")),
                momentum=_normal(row.get("rs_momentum")))
            if region == "Global":
                # GLOBAL -> SECTOR and GLOBAL -> FACTOR, including signals
                # whose constituent membership data is unavailable.
                link("root", sid)
            elif kind == "sector":
                link(country_id, sid)
        if not valid_edges:
            continue
        # A company's identity is scoped by region to avoid accidentally
        # merging identically named but unrelated instruments.
        for row in memberships.to_dict("records"):
            source_id, kind = _normal(row.get("source_id")), _normal(row.get("kind")).lower()
            source_node = lookup.get((kind, source_id))
            company_key = _normal(row.get("company_key"))
            if not source_node or not company_key:
                continue
            cid = f"{region}:company:{company_key}"
            label = _normal(row.get("Ticker")) or _normal(row.get("Company")) or company_key
            put(cid, label=label, name=_normal(row.get("Company")), kind="company", country=region)
            if region == "Global":
                # GLOBAL -> COMPANY independently of sector/factor membership.
                link("root", cid)
            if kind == "sector":
                link(source_node, cid)
            else:
                link(cid, source_node)
    return nodes, sorted(edges), diagnostics


def _relations(nodes: dict, edges: list[tuple[str, str]]):
    countries = defaultdict(set)
    sectors = defaultdict(set)  # sector -> companies
    factors = defaultdict(set)  # company -> factors
    company_sectors = defaultdict(set)
    company_factors = defaultdict(set)
    for a, b in edges:
        if a == "root" and nodes[b]["kind"] == "country":
            countries[a].add(b)
        elif nodes[a]["kind"] == "sector" and nodes[b]["kind"] == "company":
            sectors[a].add(b)
            company_sectors[b].add(a)
        elif nodes[a]["kind"] == "company" and nodes[b]["kind"] == "factor":
            factors[a].add(b)
            company_factors[a].add(b)
    return sectors, company_sectors, company_factors


def _select(nodes, edges, chosen_countries=(), chosen_sectors=(), chosen_companies=(),
            chosen_factors=(), chosen_rotations=(), match="Any selected", limit=70,
            show_context=True):
    """Return visible/highlighted graph with genuinely conjunctive ALL semantics."""
    sectors, comp_sectors, comp_factors = _relations(nodes, edges)
    all_companies = {nid for nid, n in nodes.items() if n["kind"] == "company"}
    criterion_sets = []
    for values, reverse in ((chosen_sectors, sectors),
                            (chosen_factors, {f: {c for c, fs in comp_factors.items() if f in fs}
                                              for f in chosen_factors})):
        for nid in values:
            criterion_sets.append(set(reverse.get(nid, set())))
    for cid in chosen_companies:
        criterion_sets.append({cid} if cid in all_companies else set())
    for country in chosen_countries:
        criterion_sets.append({c for c in all_companies if nodes[c]["country"] == country})
    for rotation in chosen_rotations:
        criterion_sets.append({c for c in all_companies if any(
            nodes[s].get("quadrant") == rotation for s in comp_sectors.get(c, set())) or any(
            nodes[f].get("quadrant") == rotation for f in comp_factors.get(c, set()))})
    if criterion_sets:
        matched = (set.intersection(*criterion_sets) if match == "All selected"
                   else set.union(*criterion_sets))
    else:
        matched = all_companies
    matched_full = set(matched)
    if limit is not None:
        matched = set(sorted(matched, key=lambda c: (nodes[c]["label"].lower(), c))[:limit])
    visible = {"root"}
    visible.update(n for n, x in nodes.items() if x["kind"] == "country")
    # Keep sector signals visible even if no companies qualify (context overview).
    # Include direct Global factor signals even with no company membership.
    if show_context:
        visible.update(n for n, x in nodes.items() if x["kind"] == "sector"
                       or (x["kind"] == "factor" and x.get("country") == "Global"))
    visible.update(chosen_sectors)
    visible.update(chosen_factors)
    visible.update(matched)
    for c in matched:
        visible.update(comp_sectors.get(c, set()))
        visible.update(comp_factors.get(c, set()))
    # A factor can exist without any matching company: show it when explicitly selected.
    visible = {v for v in visible if v in nodes}
    keep_edges = [(a, b) for a, b in edges if a in visible and b in visible]
    return visible, keep_edges, matched, len(matched_full)


def _plot(nodes, edges, matched, visible, height=680):
    groups = [[], [], [], [], []]
    rank = {"root": 0, "country": 1, "sector": 2, "company": 3, "factor": 4}
    for nid in visible:
        groups[rank[nodes[nid]["kind"]]].append(nid)
    for group in groups:
        group.sort(key=lambda n: (nodes[n].get("country") or "", nodes[n]["label"].lower(), n))
    positions = {}
    for col, group in enumerate(groups):
        for idx, nid in enumerate(group):
            positions[nid] = (col, 1 - (idx + .5) / max(1, len(group)))
    fig = go.Figure()
    # Separate highlighted and contextual relationship traces.
    for direct_global in (False, True):
        for active in (False, True):
            xs, ys = [], []
            for a, b in edges:
                if (a == "root" and nodes[b].get("country") == "Global") != direct_global:
                    continue
                if ((nodes[a]["kind"] == "company" and a in matched or
                     nodes[b]["kind"] == "company" and b in matched) != active):
                    continue
                xs.extend((positions[a][0], positions[b][0], None))
                ys.extend((positions[a][1], positions[b][1], None))
            if xs:
                fig.add_trace(go.Scattergl(x=xs, y=ys, mode="lines", hoverinfo="skip",
                    line={"color": ("#e1b5ff" if direct_global else "#52e0c4")
                          if active else ("#9171aa" if direct_global else "#63718a"),
                          "width": 1.4 if direct_global else 1.65 if active else .9},
                    opacity=.52 if direct_global else .65 if active else .24, showlegend=False))
    for index, kind in enumerate(("root", "country", "sector", "company", "factor")):
        ids = groups[index]
        if not ids:
            continue
        tooltips = []
        for nid in ids:
            n = nodes[nid]
            tip = f"<b>{n['label']}</b><br>Type: {kind.title()}"
            if n.get("country"):
                tip += f"<br>Source region: {n['country']}"
            if n.get("quadrant"):
                tip += f"<br>Rotation: {n['quadrant']}<br>RS: {n.get('rs','')}<br>Momentum: {n.get('momentum','')}"
            if n.get("name"):
                tip += f"<br>{n['name']}"
            tooltips.append(tip)
        fig.add_trace(go.Scattergl(x=[positions[n][0] for n in ids],
            y=[positions[n][1] for n in ids], mode="markers+text",
            marker={"size": [16 if kind in ("root", "country") else 10 if n in matched else 7 for n in ids],
                    "color": [("#52e0c4" if n in matched else COLORS.get(nodes[n].get("quadrant"),
                               {"root": "#75e4cf", "country": "#cdd7e6", "sector": "#81b8f8",
                                "company": "#9aa8bd", "factor": "#bdaaf2"}[kind])) for n in ids]},
            text=[nodes[n]["label"] if kind != "company" or n in matched and len(ids) <= 35 else "" for n in ids],
            textposition="middle right" if kind != "root" else "top center",
            textfont={"size": 10, "color": "#e5edf7"}, hovertext=tooltips,
            hovertemplate="%{hovertext}<extra></extra>", showlegend=False))
    for i, caption in enumerate(("GLOBAL", "COUNTRY", "SECTORS", "COMPANIES", "FACTORS")):
        fig.add_annotation(x=i, y=1.05, text=f"<b>{caption}</b>", showarrow=False,
                           font={"size": 13, "color": "#f2f6ff"})
    fig.update_layout(height=height, paper_bgcolor=BG, plot_bgcolor=BG,
        margin={"l": 85, "r": 110, "t": 65, "b": 30},
        xaxis={"visible": False, "range": [-.35, 4.45], "fixedrange": True},
        yaxis={"visible": False, "range": [-.04, 1.1]},
        dragmode="pan", hovermode="closest", font={"color": "#e5edf7"})
    return fig


def _selector(label, options, selected=(), key=""):
    return st.multiselect(label, options=options, default=list(selected), key=key)


def render_capital_network():
    """Streamlit entrypoint used by app.py's existing capital-network route."""
    st.title("Global Capital Intelligence Network")
    st.caption("GLOBAL → COUNTRY → SECTORS → COMPANIES → FACTORS · Plus GLOBAL direct links to its own sectors, companies and factors · Memberships, not measured fund flows")
    period = st.radio("Lookback", PERIODS, index=1, horizontal=True, key="cap_period")
    nodes, edges, diagnostics = _graph_data(period)
    if not edges or not any(n["kind"] == "company" for n in nodes.values()):
        st.error("No verified company memberships available. Run the Refresh Knowledge Graphs GitHub Action and confirm the *_edges.csv files are deployed.")
        st.json(diagnostics)
        return
    missing = [region for region, stats in diagnostics.items() if not stats["signals_valid"] or not stats["edges_valid"]]
    if missing:
        st.warning("Some datasets are missing or incomplete: " + ", ".join(missing) + ". Country relationships will be incomplete.")
    st.info("USA and India connect through their country nodes. Global-scoped sectors, companies and factors connect directly to GLOBAL and are not assigned to an unsupported country. Purple lines indicate direct Global connections.")
    tabs = ("Overview", "Sector / Factor", "Individual Companies")
    mode = st.radio("View", tabs, horizontal=True, key="cap_view")
    listing = lambda kind: sorted((n for n, x in nodes.items() if x["kind"] == kind),
                                  key=lambda n: (nodes[n]["label"].casefold(), n))
    options = lambda ids: {f"{nodes[n]['label']}  [{nodes[n].get('country') or 'Global'} · {n.split(':')[-1]}]": n for n in ids}
    country_opts = {"United States": "USA", "India": "India", "Global (direct holdings)": "Global"}
    sector_opts = options(listing("sector"))
    factor_opts = options(listing("factor"))
    company_opts = options(listing("company"))
    with st.expander("Filters · select multiple values", expanded=(mode != "Overview")):
        col1, col2, col3 = st.columns(3)
        with col1:
            chosen_countries = _selector("Countries", list(country_opts), key="cap_countries")
            chosen_rotations = _selector("Sector / Factor rotation", list(QUADRANTS), key="cap_rotations")
        with col2:
            chosen_sectors = _selector("Sectors", list(sector_opts), key="cap_sectors")
            chosen_factors = _selector("Factors", list(factor_opts), key="cap_factors")
        with col3:
            chosen_companies = _selector("Individual companies", list(company_opts), key="cap_companies")
            match = st.radio("Match filters", ("Any selected", "All selected"), horizontal=True, key="cap_match")
    filters_active = any((chosen_countries, chosen_rotations, chosen_sectors, chosen_factors, chosen_companies))
    if mode == "Individual Companies" and not chosen_companies:
        st.caption("Select one or more companies to focus on their full sector and factor memberships.")
    show_all = st.checkbox("Show all matching companies (may be slow)", value=False, key="cap_all")
    limit = None if show_all else (45 if mode == "Overview" else 90)
    visible, graph_edges, highlighted, full_count = _select(
        nodes, edges, [country_opts[c] for c in chosen_countries],
        [sector_opts[s] for s in chosen_sectors],
        [company_opts[c] for c in chosen_companies],
        [factor_opts[f] for f in chosen_factors], chosen_rotations,
        match, limit, show_context=(mode == "Overview" or not filters_active))
    st.caption(f"{full_count:,} matching companies · {len(highlighted):,} shown · {len(graph_edges):,} visible connections")
    st.plotly_chart(_plot(nodes, graph_edges, highlighted, visible), use_container_width=True,
                    config={"displaylogo": False, "scrollZoom": True})
    if full_count > len(highlighted):
        st.info("The default view limits company nodes for readability. Select 'Show all matching companies' to display every verified match.")
    with st.expander("Matching companies and connected memberships"):
        sector_rel, company_sectors, company_factors = _relations(nodes, edges)
        detail_rows = [{"Country scope": nodes[c]["country"],
                        "Company": nodes[c].get("name") or nodes[c]["label"],
                        "Ticker": nodes[c]["label"],
                        "Sectors": ", ".join(sorted(nodes[s]["label"] for s in company_sectors[c])),
                        "Factors": ", ".join(sorted(nodes[f]["label"] for f in company_factors[c]))}
                       for c in sorted(highlighted)]
        st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)
