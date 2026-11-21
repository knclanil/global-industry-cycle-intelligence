"""Sector / Factor / Holdings research workspace for Global, USA and India.

Read-only: uses the materialized `data/dashboard_cache/{region}_*.csv` snapshots.
No inferred ETF membership, price rotation, or financial observations.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "dashboard_cache"
COLORS = {"background": "#0B1220", "panel": "#142137", "text": "#E7EEF9",
          "sector": "#5AC8FA", "factor": "#C4A1FF", "company": "#59D6B1"}
METRICS = {"revenue": "Revenue", "net_income": "Net income", "roe": "ROE",
           "operating_margin": "Operating margin", "net_margin": "Net margin", "pe": "P/E"}


def _stamp(path: Path) -> int:
    return path.stat().st_mtime_ns if path.is_file() else 0


@st.cache_data(show_spinner=False, max_entries=60)
def _read_csv(path: str, timestamp: int) -> pd.DataFrame:
    if not timestamp:
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError, UnicodeError, ValueError):
        return pd.DataFrame()


def load(region: str, table: str) -> pd.DataFrame:
    if region not in {"Global", "USA", "India"}:
        raise ValueError(f"Unknown region: {region}")
    path = CACHE / f"{region.lower()}_{table}.csv"
    return _read_csv(str(path), _stamp(path)).copy()


def _split(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return list(dict.fromkeys(x.strip() for x in str(value).split(" | ") if x.strip()))


def _col(df: pd.DataFrame, name: str, default: str = "") -> pd.Series:
    return df[name].fillna("").astype(str) if name in df else pd.Series(default, index=df.index, dtype=str)


def _matching(series: pd.Series, selected: list[str]) -> pd.Series:
    if not selected:
        return pd.Series(True, index=series.index)
    wanted = set(selected)
    return series.apply(lambda s: bool(wanted.intersection(_split(s))))


def filter_companies(df: pd.DataFrame, countries=(), sectors=(), factors=(), source_indices=(),
                     query="", mode="ANY") -> pd.DataFrame:
    """Within each filter group selected values mean OR; across groups they mean AND.

    `mode='ALL'` requires every chosen sector/factor/source membership within its own group.
    Country and text filtering always narrow the result.
    """
    if df.empty:
        return df.copy()
    mask = pd.Series(True, index=df.index)
    if countries:
        mask &= _col(df, "country").isin(countries)
    for column, selected in (("sector_indices", sectors), ("factor_families", factors),
                             ("factor_indices", source_indices)):
        if selected:
            wanted = set(selected)
            values = _col(df, column).apply(lambda s: set(_split(s)))
            if mode == "ALL":
                mask &= values.apply(lambda v: wanted.issubset(v))
            else:
                mask &= values.apply(lambda v: bool(wanted & v))
    if query.strip():
        needle = query.strip().casefold()
        mask &= (_col(df, "symbol") + " " + _col(df, "company_name")).str.casefold().str.contains(
            needle, regex=False, na=False)
    return df.loc[mask].copy()


def company_intersections(df: pd.DataFrame) -> pd.DataFrame:
    """Distinct-company sector × factor overlaps built from verified membership strings.

    Missing memberships are not assigned. Duplicate index memberships do not double-count.
    """
    rows = []
    for number, row in df.reset_index(drop=True).iterrows():
        ident = str(row.get("company_key") or row.get("isin") or row.get("symbol") or number)
        for sector in _split(row.get("sector_indices", "")):
            for factor in _split(row.get("factor_families", "")):
                rows.append((ident, sector, factor))
    if not rows:
        return pd.DataFrame(columns=["sector_index", "factor_family", "companies"])
    pairs = pd.DataFrame(rows, columns=["company", "sector_index", "factor_family"]).drop_duplicates()
    return (pairs.groupby(["sector_index", "factor_family"], as_index=False)
            .agg(companies=("company", "nunique")))


def _options(df: pd.DataFrame, name: str) -> list[str]:
    options = set()
    for value in _col(df, name):
        options.update(_split(value))
    return sorted(options, key=str.casefold)


def _show_table(df: pd.DataFrame, columns: dict[str, str], *, height=430) -> None:
    names = [c for c in columns if c in df]
    if names:
        st.dataframe(df[names].rename(columns=columns), hide_index=True,
                     use_container_width=True, height=height)
    else:
        st.info("The saved snapshot does not contain the expected columns.")


def _download(region: str, label: str, df: pd.DataFrame, key: str) -> None:
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                       file_name=f"{region.lower()}_{label}.csv", mime="text/csv", key=key)


def _heatmap(matrix: pd.DataFrame, region: str) -> None:
    if matrix.empty:
        st.info("No verified Sector × Factor intersections in this selection."
                " Try clearing the filters or refreshing constituent snapshots.")
        return
    grid = matrix.pivot_table(index="sector_index", columns="factor_family", values="companies",
                              aggfunc="sum", fill_value=0)
    fig = go.Figure(go.Heatmap(z=grid.to_numpy(), x=grid.columns.tolist(), y=grid.index.tolist(),
                               colorscale=[[0, "#142137"], [.5, "#236C88"], [1, "#5AD0EA"]],
                               hovertemplate="Sector: %{y}<br>Factor: %{x}<br>Companies: %{z}<extra></extra>"))
    fig.update_layout(height=max(420, min(850, len(grid)*36+110)),
                      margin=dict(l=15,r=15,t=36,b=15), paper_bgcolor=COLORS["background"],
                      plot_bgcolor=COLORS["background"], font_color=COLORS["text"], xaxis_side="top")
    st.plotly_chart(fig, use_container_width=True, key=f"ws_heatmap_{region}")


def _coverage(df: pd.DataFrame, region: str) -> None:
    available = [c for c in METRICS if c in df]
    if not available:
        st.info("Financial statements are not present in these company snapshots."
                " Holdings membership does not establish financial statement coverage.")
        return
    numbers = df[available].apply(pd.to_numeric, errors="coerce")
    counts = numbers.notna().sum()
    if counts.empty or int(counts.max()) == 0:
        st.info("No verified financial numbers in this selection.")
        return
    a,b = st.columns([1,2])
    with a:
        st.metric("Companies with any financial metric", f"{numbers.notna().any(axis=1).sum():,}")
    with b:
        st.bar_chart(counts.rename(index=METRICS), horizontal=True)
    shown = df.loc[numbers.notna().any(axis=1)].copy()
    _show_table(shown, {"symbol":"Ticker", "company_name":"Company", **METRICS})


def render_analysis(region: str) -> None:
    """Main redesigned Sector / Factor / Holdings research page."""
    icon = {"Global":"🌍", "USA":"🇺🇸", "India":"🇮🇳"}.get(region, "🌐")
    st.title(f"{icon} {region} Sector · Factor · Holdings")
    st.caption("Discover which verified companies overlap sectors and factors, where ETFs hold the same"
               " companies, and how complete their financial-data coverage is."
               " Data is loaded from saved repository snapshots—not live price classifications.")
    companies, indices = load(region, "companies"), load(region, "indices")
    if companies.empty and indices.empty:
        st.warning("No materialized source snapshots found. Run the dashboard cache refresh workflow.")
        return

    with st.expander("Filters · select multiple values", expanded=True):
        x,y,z = st.columns(3)
        countries = x.multiselect("Company country", sorted(x for x in _col(companies,"country").unique() if x),
                                  key=f"hw_country_{region}")
        sector = y.multiselect("Sector source(s)", _options(companies,"sector_indices"),
                               key=f"hw_sector_{region}")
        factor = z.multiselect("Factor family/families", _options(companies,"factor_families"),
                               key=f"hw_factor_{region}")
        a,b,c = st.columns([2,1,1])
        query = a.text_input("Find company / ticker", key=f"hw_find_{region}")
        match = b.radio("Within selected groups", ["ANY", "ALL"], horizontal=True,
                        help="Selected groups combine with AND. ANY/ALL applies within each sector and factor group.",
                        key=f"hw_match_{region}")
        # No source-level filter in the default interface: families and sectors avoid duplicate index names.
        only_overlap = c.checkbox("Sector & factor members only", key=f"hw_both_{region}")

    selected = filter_companies(companies, countries, sector, factor, query=query, mode=match)
    if only_overlap and not selected.empty:
        selected = selected[_col(selected,"sector_indices").ne("") & _col(selected,"factor_families").ne("")]
    verified = len(selected)
    matched_memberships = pd.to_numeric(selected.get("index_memberships",pd.Series(dtype=float)),errors="coerce").sum()
    sector_count = len(_options(selected,"sector_indices"))
    factor_count = len(_options(selected,"factor_families"))
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Matching companies", f"{verified:,}")
    m2.metric("Sector sources represented", f"{sector_count:,}")
    m3.metric("Factor families represented", f"{factor_count:,}")
    m4.metric("Total source memberships", f"{matched_memberships:,.0f}")

    overview, holdings, intersections, sources, financial = st.tabs([
        "Overview", "Company explorer", "Sector × Factor overlap", "Index / ETF directory", "Financial coverage"])
    with overview:
        st.subheader("What is connected?")
        if selected.empty:
            st.info("No companies match these filters. Clear some selections to see relationships.")
        else:
            counts = defaultdict(set)
            for _, row in selected.iterrows():
                ident = str(row.get("company_key") or row.get("isin") or row.get("symbol") or _)
                for s in _split(row.get("sector_indices", "")):
                    counts[("Sector",s)].add(ident)
                for f in _split(row.get("factor_families", "")):
                    counts[("Factor",f)].add(ident)
            chart = pd.DataFrame([{"Type":kind,"Group":name,"Companies":len(people)}
                                  for (kind,name),people in counts.items()])
            if not chart.empty:
                chart = chart.sort_values("Companies", ascending=False).head(25)
                fig = go.Figure()
                for kind,color in (("Sector",COLORS["sector"]),("Factor",COLORS["factor"])):
                    part=chart.loc[chart.Type.eq(kind)]
                    fig.add_trace(go.Bar(y=[f"{kind} · {n}" for n in part.Group], x=part.Companies,
                                         orientation="h",name=kind,marker_color=color))
                fig.update_layout(height=max(380,len(chart)*27+100),barmode="group",margin=dict(l=10,r=10,t=20,b=10),
                                  paper_bgcolor=COLORS["background"],plot_bgcolor=COLORS["background"],
                                  font_color=COLORS["text"],yaxis=dict(autorange="reversed"),
                                  xaxis_title="Distinct companies")
                st.plotly_chart(fig,use_container_width=True,key=f"hw_overview_{region}")
            st.caption("Counts represent distinct companies within each sector source or factor family."
                       " A company may appear in multiple groups.")
    with holdings:
        st.subheader("Company membership explorer")
        if selected.empty:
            st.info("No matching holdings records.")
        else:
            _show_table(selected, {"symbol":"Ticker", "company_name":"Company", "country":"Country",
              "industry":"Reported industry", "sector_indices":"Sector indices / ETFs",
              "factor_families":"Factor families", "factor_indices":"Factor source indices / ETFs",
              "index_memberships":"Membership count", "avg_etf_weight_pct":"Mean ETF weight (%)"}, height=550)
            _download(region,"filtered_holdings",selected,f"hw_export_{region}")
    with intersections:
        st.subheader("Sector × Factor overlap")
        st.caption("Number of DISTINCT matching companies with both a given sector-source membership"
                   " and a verified factor-family membership. No inferred company links.")
        matrix = company_intersections(selected)
        _heatmap(matrix,region)
        with st.expander("Overlap counts as a table"):
            _show_table(matrix,{"sector_index":"Sector source","factor_family":"Factor family",
                                "companies":"Distinct companies"})
            if not matrix.empty:
                _download(region,"sector_factor_overlap",matrix,f"hw_matrix_export_{region}")
    with sources:
        st.subheader("Index and ETF sources")
        st.caption("Source inventory is regional; holdings filters above apply to companies, not to"
                   " the total constituent counts stored for each source.")
        if indices.empty:
            st.info("No source index records available.")
        else:
            search=st.text_input("Find an index or ETF",key=f"hw_index_find_{region}")
            src=indices.copy()
            if search:
                src=src[_col(src,"index_name").str.contains(search,case=False,regex=False)]
            _show_table(src,{"index_name":"Source","category":"Category","factor_family":"Factor family",
                             "constituents":"Total constituents","snapshot_utc":"Snapshot date"})
            _download(region,"source_indices",src,f"hw_sources_export_{region}")
    with financial:
        st.subheader("Financial statement coverage")
        _coverage(selected,region)
        st.caption("Unavailable financial values remain missing. Never interpret blank data as zero.")
    with st.expander("Data quality & methodology"):
        manifest=CACHE/"manifest.json"
        if manifest.exists():
            try:
                st.caption(f"Dashboard cache built: {json.loads(manifest.read_text()).get('built_utc','Unknown')}")
            except (OSError,ValueError):
                pass
        st.caption("Sector/source overlap is derived from membership lists in the company snapshot."
                   " It is not a rotation ranking, trading signal, or financial forecast.")


def render_graph(region: str) -> None:
    """Backwards-compatible holdings graph entry point for older routes."""
    st.title(f"{region} Holdings Network")
    st.caption("Explore verified sector and factor memberships in the redesigned research workspace.")
    render_analysis(region)
