"""Global / USA / India: rotation -> sector -> company -> factor graph.

Requires existing rotation_graph_evidence.py and generated *_signals.csv / *_edges.csv.
Sector and factor rotation classes describe the *index*, not the company price.
"""
from __future__ import annotations

import json
import re
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



# Presentation identity only: never alter index-level membership CSVs or rotation signals.
# Prefer canonical family names over broad substring matches ("Growth" != "Value").
FACTOR_RULES = (
    (r"(?:low|min(?:imum)?)\s*volatility", "Low Volatility"),
    (r"(?:dividend|yield)", "Dividend Yield"),
    (r"equal\s*weight", "Equal Weight"),
    (r"small\s*cap|russell\s*2000", "Small Cap"),
    (r"\bmomentum\b", "Momentum"),
    (r"\bquality\b", "Quality"),
    (r"\bvalue\b", "Value"),
    (r"\bgrowth\b", "Growth"),
    (r"\balpha\b", "Alpha"),
    (r"\bsize\b", "Size"),
)


def _factor_family(label: str) -> str:
    value = re.sub(r"[()_\-]+", " ", str(label)).strip()
    for pattern, canonical in FACTOR_RULES:
        if re.search(pattern, value, flags=re.IGNORECASE):
            return canonical
    return re.sub(r"\s+", " ", value) or "Unclassified factor"


def _display_group(node: dict) -> tuple[str, str]:
    # Do not deduplicate sectors with different economic meanings. Only
    # identical normalized sector labels share a visual node.
    if node["type"] == "factor":
        value = _factor_family(node["label"])
    else:
        value = re.sub(r"\s+", " ", str(node["label"]).strip())
    return node["type"], value.casefold()


def _collapse_sources(nodes: list[dict]):
    """Merge visual nodes but preserve raw source ids, quadrant evidence and metrics."""
    grouped = {}
    origin_to_group = {}
    for n in nodes:
        key = _display_group(n)
        if key not in grouped:
            group_id = f"g:{n['type']}:{key[1]}"
            grouped[key] = {"id": group_id,
                            "label": _factor_family(n['label']) if n['type'] == 'factor' else n['label'],
                            "name": _factor_family(n['label']) if n['type'] == 'factor' else n['label'],
                            "type": n['type'], "quadrant": n['quadrant'],
                            "raw_sources": [], "quadrants": set(), "source_labels": []}
        g = grouped[key]
        g["raw_sources"].append(n["id"])
        g["quadrants"].add(n["quadrant"])
        g["source_labels"].append(f"{n['label']} [{n['quadrant']}]")
        origin_to_group[n["id"]] = g["id"]
    result = []
    for g in grouped.values():
        g["quadrants"] = tuple(q for q in (*QUADRANTS, "Unavailable") if q in g["quadrants"])
        g["quadrant"] = g["quadrants"][0] if len(g["quadrants"]) == 1 else "Mixed"
        g["source_labels"] = sorted(set(g["source_labels"]))
        result.append(g)
    return sorted(result, key=lambda n: (n["label"].casefold(), n["id"])), origin_to_group


def filter_company_memberships(edges: pd.DataFrame, rotations=(), sectors=(),
                               factors=(), companies=(), match_mode="Any selected",
                               include_other_memberships=False) -> pd.DataFrame:
    """Filter the RAW verified membership rows, independent of graph state.

    A sector/factor choice selects a company cohort (ANY or ALL selected
    categories). Rows for the chosen categories are shown by default. With
    include_other_memberships=True, show all evidence for companies in cohort.
    No graph node caps or visual selections are applied here.
    """
    if edges.empty:
        return edges.copy()
    required = {"company_key", "quadrant", "kind", "label"}
    if not required.issubset(edges.columns):
        return edges.iloc[0:0].copy()
    df = edges.copy()
    # CSVs can contain blank/mixed values. Group factor index variants together
    # without losing their original source_id/portfolio_id in the output.
    for col in ("company_key", "quadrant", "kind", "label"):
        df[col] = df[col].fillna("").astype(str)
    df["__family"] = [(_factor_family(label) if kind == "factor" else label.strip())
                       for kind, label in zip(df["kind"], df["label"])]
    if rotations:
        df = df.loc[df["quadrant"].isin(rotations)]
    if companies:
        df = df.loc[df["company_key"].isin(companies)]
    if df.empty:
        return df.drop(columns="__family").reset_index(drop=True)
    criteria = [("sector", value) for value in sectors] + [("factor", value) for value in factors]
    if criteria:
        key_sets = [set(df.loc[(df["kind"] == kind) &
                               (df["__family"].str.casefold() == value.casefold()),
                               "company_key"])
                    for kind, value in criteria]
        if match_mode == "All selected":
            matched = set.intersection(*key_sets)
        else:
            matched = set.union(*key_sets)
        df = df[df["company_key"].isin(matched)]
        if not include_other_memberships:
            selected = {(kind, value.casefold()) for kind, value in criteria}
            df = df.loc[[ (kind, family.casefold()) in selected
                          for kind, family in zip(df["kind"], df["__family"]) ]]
    return df.drop(columns="__family").drop_duplicates().reset_index(drop=True)


def _draw(nodes, links, selection: str | list[str] | dict, max_companies: int | None,
          match_mode: str = "Any selected"):
    by_id = {n["id"]: n for n in nodes}
    raw_sectors, raw_factors, companies, members, company_sources = _choose_visible(
        nodes, links, selection, max_companies, match_mode)
    sectors, sector_map = _collapse_sources(raw_sectors)
    factors, factor_map = _collapse_sources(raw_factors)
    visible_company_ids = {n["id"] for n in companies}
    raw_source_ids = {n["id"] for n in raw_sectors + raw_factors}
    positions = {f"q:{q}": (0., 1 - (i + .5) / len(QUADRANTS))
                 for i, q in enumerate(QUADRANTS)}
    for x, group in ((1., sectors), (2.15, companies), (3.3, factors)):
        for i, node in enumerate(group):
            positions[node["id"]] = (x, 1 - (i + .5) / max(1, len(group)))
    fig = go.Figure()
    paths = {q: set() for q in (*QUADRANTS, 'Unavailable')}
    # Every original source is processed separately. Multiple Nifty indexes
    # mapped to the same factor share one displayed node and unique edge.
    for source in raw_sectors:
        q, sid = source["quadrant"], source["id"]
        gid = sector_map[sid]
        paths[q].add((f"q:{q}", gid))
        paths[q].update((gid, cid) for cid in members.get(sid, ())
                        if cid in visible_company_ids)
    for source in raw_factors:
        q, sid = source["quadrant"], source["id"]
        gid = factor_map[sid]
        matched = set(members.get(sid, ())) & visible_company_ids
        for cid in matched:
            paths[q].add((cid, gid))
            if q != "Unavailable" and not any((s in raw_source_ids and by_id[s]["type"] == "sector"
                        and by_id[s]["quadrant"] == q)
                       for s in company_sources.get(cid, ())):
                paths[q].add((f"q:{q}", cid))
        if not matched and q in QUADRANTS:
            paths[q].add((f"q:{q}", gid))
    # Factor memberships without a valid rotation are drawn in neutral gray.
    # They must never be represented as Leading/Improving/Weakening/Lagging.
    for quadrant in (*QUADRANTS, 'Unavailable'):
        xs, ys = [], []
        for start, end in sorted(paths[quadrant]):
            if start not in positions or end not in positions:
                continue
            a, b = positions[start], positions[end]
            xs.extend((a[0], b[0], None))
            ys.extend((a[1], b[1], None))
        if xs:
            fig.add_trace(go.Scattergl(x=xs, y=ys, mode="lines",
                                      line=dict(color=PALETTE.get(quadrant, "#94a3b8"), width=1.2),
                                      opacity=.36, hoverinfo="skip", showlegend=False))

    def add_nodes(group, title, color, size, symbol="circle", display_text=True):
        if not group:
            return
        hover = []
        for n in group:
            detail = f"<b>{n.get('name') or n['label']}</b>"
            if n.get("raw_sources"):
                detail += "<br>Original index signals: " + str(len(n["raw_sources"]))
                detail += "<br>Rotations: " + ", ".join(n["quadrants"])
                detail += "<br>Indexes: " + "<br>".join(n["source_labels"][:30])
                if len(n["source_labels"]) > 30:
                    detail += "<br>… more indexes in source table"
                related = set().union(*(members.get(s, set()) for s in n["raw_sources"]))
                detail += f"<br>Verified companies: {len(related)}"
            hover.append(detail)
        fig.add_trace(go.Scattergl(
            x=[positions[n["id"]][0] for n in group],
            y=[positions[n["id"]][1] for n in group],
            mode="markers+text" if display_text else "markers",
            marker=dict(size=size, color=color, symbol=symbol),
            text=[n["label"] for n in group],
            textposition="middle left" if title == "Rotations" else "middle right",
            textfont=dict(size=11, color="#e5e7eb"),
            hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", name=title))

    filtered = isinstance(selection, dict) and selection.get("mode") == "matched"
    displayed_quadrants = ([q for q in QUADRANTS if any(
        q in n["quadrants"] for n in sectors + factors)] if filtered
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
        # Filters show each factor family once; selecting a family expands to
        # every underlying verified index signal for consistent ANY/ALL logic.
        factor_groups = defaultdict(list)
        for node in sources:
            if node["type"] == "factor":
                factor_groups[_factor_family(node["label"])].append(node["id"])
        factor_options = sorted(factor_groups, key=str.casefold)
        company_options = {n["id"]: f"{n.get('name') or n['label']} · {n['label']}"
                           for n in companies_all}
        left, right = st.columns(2)
        with left:
            selected_sectors = st.multiselect(
                "Sectors (multiple)", list(sector_options),
                format_func=lambda sid: sector_options.get(sid, sid),
                key=f"kg_sectors_{region}")
        with right:
            selected_factor_families = st.multiselect(
                "Factors (multiple)", factor_options,
                key=f"kg_factors_{region}")
            selected_factors = [sid for family in selected_factor_families
                                for sid in factor_groups[family]]
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
            # A factor family is one criterion even if it has many index ETFs.
            # Membership within each family is OR; ALL intersects criteria,
            # not the individual indices within a family.
            criteria = [set(memberships.get(sid, ())) for sid in selected_sectors]
            criteria.extend(set().union(*(memberships.get(sid, set()) for sid in factor_groups[family]))
                            for family in selected_factor_families)
            matched = (set.intersection(*criteria) if match_mode == "All selected"
                       else set.union(*criteria))
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
               f"{len(factors)} unique factor families. Overall graph: {len(nodes)} nodes / "
               f"{len(links)} relationships. No membership data is discarded.")
    st.caption("Repeated factor indexes share one visual family node; original index-level signals and memberships remain in the tables below.")
    st.info("Gray company-to-factor links represent verified factor membership with unavailable rotation. "
            "Rotation labels describe sector/factor index signals, not independent "
            "company price classifications. Factor-only companies connect to their "
            "rotation directly when no same-quadrant sector link exists.")
    with st.expander("All sector & factor signals"):
        st.dataframe(signals, use_container_width=True, hide_index=True)
    # Independent evidence-table controls. The graph and its own filters above
    # are intentionally untouched; changing these controls does not redraw it.
    with st.expander("All verified company memberships · table filters", expanded=False):
        st.caption("These filters apply ONLY to this membership table, not to the Knowledge Graph above.")
        if not edges.empty and {"company_key", "quadrant", "kind", "label"}.issubset(edges.columns):
            sector_names = sorted({str(v).strip() for v in edges.loc[
                edges["kind"].astype(str) == "sector", "label"] if str(v).strip()}, key=str.casefold)
            factor_names = sorted({_factor_family(v) for v in edges.loc[
                edges["kind"].astype(str) == "factor", "label"]}, key=str.casefold)
            company_labels = {}
            for _, row in edges.iterrows():
                key = str(row["company_key"])
                if key not in company_labels:
                    company_labels[key] = f"{row.get('Company', '')} · {row.get('Ticker', '')} ({key})"
            a, b = st.columns(2)
            with a:
                table_rotations = st.multiselect("Table rotations", list(QUADRANTS) + ["Unavailable"],
                                                 key=f"kg_table_rot_{region}_{period}")
                table_sectors = st.multiselect("Table sectors", sector_names,
                                               key=f"kg_table_sectors_{region}_{period}")
            with b:
                table_factors = st.multiselect("Table factors", factor_names,
                                               key=f"kg_table_factors_{region}_{period}")
                table_companies = st.multiselect("Table companies", sorted(company_labels),
                                                 format_func=lambda k: company_labels[k],
                                                 key=f"kg_table_companies_{region}_{period}")
            mode_col, scope_col = st.columns(2)
            with mode_col:
                table_match = st.radio("Table sector/factor matching",
                                       ["Any selected", "All selected"], horizontal=True,
                                       key=f"kg_table_match_{region}_{period}")
            with scope_col:
                all_evidence = st.checkbox("Show other memberships of matching companies",
                                           value=False, key=f"kg_table_all_evidence_{region}_{period}")
            table_rows = filter_company_memberships(
                edges, table_rotations, table_sectors, table_factors,
                table_companies, table_match, all_evidence)
        else:
            table_rows = edges.copy()
        st.caption(f"{len(table_rows):,} verified membership records · "
                   f"{table_rows['company_key'].nunique() if 'company_key' in table_rows else 0:,} companies. "
                   "Graph selection and company display limits do not affect this table.")
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
        st.download_button("Download table memberships CSV",
                           data=table_rows.to_csv(index=False).encode("utf-8"),
                           file_name=f"{region.lower()}_{period}_table_memberships.csv",
                           mime="text/csv", key=f"kg_table_export_{region}_{period}")
    with st.expander("Unmapped source records"):
        st.dataframe(_load(region, period, "unmapped"), use_container_width=True, hide_index=True)
