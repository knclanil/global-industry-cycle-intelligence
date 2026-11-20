"""Capital membership network: GLOBAL -> ROTATION -> COUNTRY -> SECTOR -> COMPANY -> FACTOR.

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
# All markets tracked in country_market_data.py. Country nodes represent
# market coverage, NOT proof of country-specific sector/company memberships.
COUNTRY_MARKETS = {
    "SPY": "United States", "INDA": "India", "EWJ": "Japan",
    "MCHI": "China", "EWU": "United Kingdom", "EWG": "Germany",
    "EWQ": "France", "EWL": "Switzerland", "EWC": "Canada",
    "EWA": "Australia", "EWY": "South Korea", "EWT": "Taiwan",
    "EWZ": "Brazil", "EWW": "Mexico", "EZA": "South Africa",
    "EIDO": "Indonesia", "THD": "Thailand", "EWM": "Malaysia",
    "KSA": "Saudi Arabia", "UAE": "United Arab Emirates",
}
COUNTRY_KEYS = {"United States": "USA", "India": "India"}

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
    # Country-level rotations are based on ETF / ACWI relative strength and
    # momentum. Do not infer a country's rotation from its constituent sectors.
    rotation_file = directory / f"country_{period}_rotations.csv"
    country_rotations = {}
    if rotation_file.is_file():
        frame = _csv(str(rotation_file), rotation_file.stat().st_mtime_ns)
        if {"ETF", "Quadrant"}.issubset(frame.columns):
            country_rotations = {str(r["ETF"]): str(r["Quadrant"])
                                 for r in frame.to_dict("records")
                                 if str(r["Quadrant"]) in QUADRANTS}
    diagnostics["country_rotations"] = {"classified": len(country_rotations),
                                        "tracked": len(COUNTRY_MARKETS),
                                        "snapshot_found": rotation_file.is_file()}
    for quadrant in QUADRANTS:
        rid = f"rotation:{quadrant}"
        nodes[rid] = {"label": quadrant, "kind": "rotation", "quadrant": quadrant}
        edges.add(("root", rid))
    # Unclassified is an explicit data gap, not a fifth market rotation.
    if len(country_rotations) != len(COUNTRY_MARKETS):
        nodes["rotation:Unclassified"] = {"label": "Unclassified (missing data)",
                                          "kind": "rotation"}
        edges.add(("root", "rotation:Unclassified"))
    # Preserve every supported country as a visible node, even when that
    # market has no country-level constituent dataset yet.
    for ticker, country_name in COUNTRY_MARKETS.items():
        scope = COUNTRY_KEYS.get(country_name, ticker)
        cid = f"country:{scope}"
        quadrant = country_rotations.get(ticker, "Unclassified")
        nodes[cid] = {"label": country_name, "kind": "country",
                      "country": scope, "ticker": ticker, "quadrant": quadrant,
                      "coverage": "Constituents available" if country_name in COUNTRY_KEYS else
                                  "Country market tracked; constituent data unavailable"}
        edges.add((f"rotation:{quadrant}", cid))

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
            link(f"rotation:{nodes[country_id].get('quadrant', 'Unclassified')}", country_id)

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
    """Filter to the connected subgraph; never leave unrelated countries/sources.

    Within countries, companies, and rotations, multi-select values are ORed.
    Selected sectors/factors use the requested Any/All logic. Distinct filter
    categories must all match (AND). Company membership cross-links are kept.
    """
    sectors, comp_sectors, comp_factors = _relations(nodes, edges)
    all_companies = {nid for nid, n in nodes.items() if n["kind"] == "company"}
    active = any((chosen_countries, chosen_sectors, chosen_companies,
                  chosen_factors, chosen_rotations))
    if not active:
        matched = all_companies
    else:
        categories = []
        if chosen_countries:
            categories.append({c for c in all_companies
                               if nodes[c].get("country") in chosen_countries})
        if chosen_companies:
            categories.append(set(chosen_companies) & all_companies)
        if chosen_rotations:
            # Country ETF rotation takes precedence for country-scoped branches;
            # the direct Global branch has no country ETF and uses its own
            # sector/factor signals instead.
            categories.append({c for c in all_companies if (
                nodes.get(f"country:{nodes[c].get('country')}", {}).get("quadrant")
                    in chosen_rotations
                if nodes[c].get("country") != "Global" else
                any(nodes[s].get("quadrant") in chosen_rotations
                    for s in comp_sectors.get(c, set()) | comp_factors.get(c, set())))})
        selected_source_sets = [set(sectors.get(s, ())) for s in chosen_sectors]
        selected_source_sets.extend(
            {c for c, fs in comp_factors.items() if f in fs}
            for f in chosen_factors)
        if selected_source_sets:
            source_matches = (set.intersection(*selected_source_sets)
                              if match == "All selected" else
                              set.union(*selected_source_sets))
            categories.append(source_matches)
        matched = set.intersection(*categories) if categories else set()
    matched_full = set(matched)
    if limit is not None:
        matched = set(sorted(matched, key=lambda c: (
            nodes[c]["label"].casefold(), c))[:limit])

    visible = {"root"}
    if not active and show_context:
        visible.update(nid for nid, n in nodes.items()
                       if n["kind"] in ("rotation", "country", "sector", "factor"))
    else:
        # Explicit source choices remain visible even if there are no companies.
        visible.update(s for s in chosen_sectors if s in nodes)
        visible.update(f for f in chosen_factors if f in nodes)
        # Country-only and rotation-only filters still show their source signals
        # even when constituents are not yet available.
        if chosen_countries:
            visible.update(nid for nid, n in nodes.items()
                           if n["kind"] == "country" and
                           n.get("country") in chosen_countries and
                           (not chosen_rotations or n.get("quadrant") in chosen_rotations))
        if chosen_rotations and not (chosen_sectors or chosen_factors or chosen_companies):
            visible.update(nid for nid, n in nodes.items()
                           if n["kind"] == "country" and
                           n.get("quadrant") in chosen_rotations and
                           (not chosen_countries or n.get("country") in chosen_countries))
            visible.update(nid for nid, n in nodes.items()
                           if n["kind"] in ("sector", "factor") and
                           n.get("quadrant") in chosen_rotations and
                           (not chosen_countries or n.get("country") in chosen_countries))
        if chosen_countries and not (chosen_rotations or chosen_sectors or chosen_factors
                                     or chosen_companies):
            visible.update(nid for nid, n in nodes.items()
                           if n["kind"] in ("sector", "factor") and
                           n.get("country") in chosen_countries)
    visible.update(matched)
    for c in matched:
        visible.update(comp_sectors.get(c, set()))
        visible.update(comp_factors.get(c, set()))
    # Only show countries that are connected to something visible, or selected.
    scopes = {nodes[n].get("country") for n in visible if n in nodes}
    visible.update(nid for nid, n in nodes.items()
                   if n["kind"] == "country" and n.get("country") in scopes)
    for nid in list(visible):
        if nodes[nid]["kind"] == "country":
            q = nodes[nid].get("quadrant", "Unclassified")
            visible.add(f"rotation:{q}")
    if not active:
        visible.update(f"rotation:{q}" for q in QUADRANTS)
    visible.add("root")
    visible &= set(nodes)
    kept_edges = [(a, b) for a, b in edges if a in visible and b in visible]
    return visible, kept_edges, matched, len(matched_full)


def _plot(nodes, edges, matched, visible, height=680):
    groups = [[], [], [], [], [], []]
    rank = {"root": 0, "rotation": 1, "country": 2,
            "sector": 3, "company": 4, "factor": 5}
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
    for index, kind in enumerate(("root", "rotation", "country", "sector", "company", "factor")):
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
                               {"root": "#75e4cf", "rotation": "#b9b8ec", "country": "#cdd7e6", "sector": "#81b8f8",
                                "company": "#9aa8bd", "factor": "#bdaaf2"}[kind])) for n in ids]},
            text=[nodes[n]["label"] if kind != "company" or n in matched and len(ids) <= 35 else "" for n in ids],
            textposition="middle right" if kind != "root" else "top center",
            textfont={"size": 10, "color": "#e5edf7"}, hovertext=tooltips,
            hovertemplate="%{hovertext}<extra></extra>", showlegend=False))
    for i, caption in enumerate(("GLOBAL", "ROTATION", "COUNTRIES", "SECTORS", "COMPANIES", "FACTORS")):
        fig.add_annotation(x=i, y=1.05, text=f"<b>{caption}</b>", showarrow=False,
                           font={"size": 13, "color": "#f2f6ff"})
    fig.update_layout(height=height, paper_bgcolor=BG, plot_bgcolor=BG,
        margin={"l": 85, "r": 110, "t": 65, "b": 30},
        xaxis={"visible": False, "range": [-.35, 5.45], "fixedrange": True},
        yaxis={"visible": False, "range": [-.04, 1.1]},
        dragmode="pan", hovermode="closest", font={"color": "#e5edf7"})
    return fig


def _selector(label, options, selected=(), key=""):
    return st.multiselect(label, options=options, default=list(selected), key=key)


def render_capital_network():
    """Streamlit entrypoint used by app.py's existing capital-network route."""
    st.title("Global Capital Intelligence Network")
    st.caption("GLOBAL → ROTATION → COUNTRY → SECTORS → COMPANIES → FACTORS · Global direct sector/company/factor branches are also preserved · Memberships, not measured fund flows")
    period = st.radio("Lookback", PERIODS, index=1, horizontal=True, key="cap_period")
    nodes, edges, diagnostics = _graph_data(period)
    if not any(n["kind"] == "company" for n in nodes.values()):
        st.warning("No verified company memberships available. Country nodes remain visible. "
                   "Run Refresh Knowledge Graphs and confirm the *_edges.csv files are deployed.")
        st.json(diagnostics)
    missing = [region for region, stats in diagnostics.items() if region in REGIONS and (not stats["signals_valid"] or not stats["edges_valid"])]
    if missing:
        st.warning("Some datasets are missing or incomplete: " + ", ".join(missing) + ". Country relationships will be incomplete.")
    status = diagnostics["country_rotations"]
    if status["classified"] < status["tracked"]:
        st.warning(f"Country rotation data: {status['classified']}/{status['tracked']} ETFs classified. "
                   "Run the country rotation snapshot builder; unclassified markets remain visible "
                   "without an invented quadrant.")
    st.info("All 20 country ETF markets are tracked. Only USA and India currently have verified "
            "country-scoped company-membership datasets; other countries may have no downstream "
            "company connections. Global-scoped sectors/companies/factors link directly to GLOBAL.")
    tabs = ("Overview", "Sector / Factor", "Individual Companies")
    mode = st.radio("View", tabs, horizontal=True, key="cap_view")
    listing = lambda kind: sorted((n for n, x in nodes.items() if x["kind"] == kind),
                                  key=lambda n: (nodes[n]["label"].casefold(), n))
    options = lambda ids: {f"{nodes[n]['label']}  [{nodes[n].get('country') or 'Global'} · {n.split(':')[-1]}]": n for n in ids}
    country_opts = {COUNTRY_MARKETS[t]: COUNTRY_KEYS.get(COUNTRY_MARKETS[t], t)
                    for t in COUNTRY_MARKETS}
    country_opts["Global (direct holdings)"] = "Global"
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
    st.caption(f"{sum(nodes[n]['kind'] == 'country' for n in visible)} visible countries (20 tracked) · {full_count:,} matching companies · "
               f"{len(highlighted):,} shown · {len(graph_edges):,} visible connections")
    unsupported = [c for c in chosen_countries if country_opts[c] not in ("USA", "India", "Global")]
    if unsupported:
        st.warning("Country-specific company data is not yet available for: " + ", ".join(unsupported)
                   + ". These countries remain visible but cannot be connected to companies "
                     "until their verified constituents are added to the builder.")
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
