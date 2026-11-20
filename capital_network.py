"""Global Capital Network from one canonical six-column membership table.

Visual path: GLOBAL -> ROTATION -> COUNTRY -> SECTOR -> COMPANY -> FACTOR.
A 'Global direct' scope represents *global* memberships; it is NOT a country
or a calculated country rotation. Missing country constituents are not invented.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs'
COUNTRIES = {
    'SPY': 'United States', 'INDA': 'India', 'EWJ': 'Japan',
    'MCHI': 'China', 'EWU': 'United Kingdom', 'EWG': 'Germany',
    'EWQ': 'France', 'EWL': 'Switzerland', 'EWC': 'Canada',
    'EWA': 'Australia', 'EWY': 'South Korea', 'EWT': 'Taiwan',
    'EWZ': 'Brazil', 'EWW': 'Mexico', 'EZA': 'South Africa',
    'EIDO': 'Indonesia', 'THD': 'Thailand', 'EWM': 'Malaysia',
    'KSA': 'Saudi Arabia', 'UAE': 'United Arab Emirates',
}
COUNTRY_REGION = {'USA': 'United States', 'India': 'India', 'Global': 'Global direct'}
ROTATIONS = ('Leading', 'Improving', 'Weakening', 'Lagging')
COLORS = {'Leading': '#31d4a1', 'Improving': '#62a9ff',
          'Weakening': '#ffc44d', 'Lagging': '#f17692',
          'Unclassified': '#9aa7ba', 'Global scope': '#aa91e5'}
COLS = ('Global', 'Rotation', 'Country', 'Sector', 'Company', 'Factor')


@st.cache_data(show_spinner=False, max_entries=60)
def _read(path: str, stamp: int) -> pd.DataFrame:
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False).fillna('')
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def read_cache(file: Path) -> pd.DataFrame:
    return _read(str(file), file.stat().st_mtime_ns if file.exists() else -1)


def _clean(value) -> str:
    return str(value or '').strip()


def build_capital_table(period: str, cache: Path = CACHE) -> tuple[pd.DataFrame, dict]:
    """Create canonical path records from verified cached membership evidence.

    Each company may have several rows: one per sector/factor combination.
    Blank cells mean that the relationship is not verified, not that it is absent.
    Extra ID columns preserve unique company and membership identities.
    """
    rotations = read_cache(cache / f'country_{period}_rotations.csv')
    country_class = {}
    if {'ETF', 'Quadrant'} <= set(rotations.columns):
        for r in rotations.to_dict('records'):
            if _clean(r['Quadrant']) in ROTATIONS:
                country_class[_clean(r['ETF']).upper()] = _clean(r['Quadrant'])

    records = []
    def add(rotation='', country='', sector='', company='', factor='', **extra):
        records.append({**dict(zip(COLS, ('Global', rotation, country, sector, company, factor))),
                        'scope': extra.get('scope', ''),
                        'sector_id': extra.get('sector_id', ''),
                        'company_id': extra.get('company_id', ''),
                        'factor_id': extra.get('factor_id', ''),
                        'sector_rotation': extra.get('sector_rotation', ''),
                        'factor_rotation': extra.get('factor_rotation', ''),
                        'ticker': extra.get('ticker', ''),
                        'company_name': extra.get('company_name', ''),
                        'coverage': extra.get('coverage', '')})

    # Every tracked country exists even if its constituents are not collected.
    for ticker, name in COUNTRIES.items():
        scope = 'USA' if ticker == 'SPY' else 'India' if ticker == 'INDA' else ticker
        add(country=name, rotation=country_class.get(ticker, 'Unclassified'),
            scope=scope, coverage='country-only' if scope not in ('USA', 'India') else 'country-memberships')

    diagnostics = {'classified_countries': len(country_class), 'tracked_countries': len(COUNTRIES)}
    for region, country in COUNTRY_REGION.items():
        scope = region
        q = ('Global scope' if region == 'Global' else
             country_class.get('SPY' if region == 'USA' else 'INDA', 'Unclassified'))
        if region == 'Global':
            add(rotation=q, country=country, scope=scope, coverage='global-direct-not-country')
        signals = read_cache(cache / f'{region.lower()}_{period}_signals.csv')
        memberships = read_cache(cache / f'{region.lower()}_{period}_edges.csv')
        if not {'source_id', 'kind', 'label'} <= set(signals.columns):
            diagnostics[f'{region}_signals'] = 'missing/invalid'
            continue
        if not {'source_id', 'kind', 'company_key'} <= set(memberships.columns):
            diagnostics[f'{region}_edges'] = 'missing/invalid'
            memberships = pd.DataFrame(columns=['source_id', 'kind', 'company_key', 'Company', 'Ticker'])

        source = {}
        for r in signals.to_dict('records'):
            kind = _clean(r.get('kind')).lower()
            if kind in ('sector', 'factor'):
                source[(kind, _clean(r.get('source_id')))] = (
                    _clean(r.get('label')) or _clean(r.get('source_id')),
                    _clean(r.get('quadrant')))
        by_company = defaultdict(lambda: {'sectors': {}, 'factors': {}, 'ticker': '', 'name': ''})
        populated_sources = set()
        for r in memberships.to_dict('records'):
            kind = _clean(r.get('kind')).lower()
            sid = _clean(r.get('source_id'))
            key = _clean(r.get('company_key'))
            if not key or (kind, sid) not in source:
                continue
            populated_sources.add((kind, sid))
            c = by_company[key]
            c['ticker'] = _clean(r.get('Ticker')) or c['ticker']
            c['name'] = _clean(r.get('Company')) or c['name']
            c['sectors' if kind == 'sector' else 'factors'][sid] = source[(kind, sid)]
        for company_key, info in by_company.items():
            sectors = list(info['sectors'].items()) or [('', ('', ''))]
            factors = list(info['factors'].items()) or [('', ('', ''))]
            cid = f'{scope}:{company_key}'
            name = info['ticker'] or info['name'] or company_key
            for sid, (sector_name, sector_q) in sectors:
                for fid, (factor_name, factor_q) in factors:
                    add(rotation=q, country=country, sector=sector_name,
                        company=name, factor=factor_name, scope=scope,
                        sector_id=f'{scope}:sector:{sid}' if sid else '',
                        company_id=cid,
                        factor_id=f'{scope}:factor:{fid}' if fid else '',
                        sector_rotation=sector_q, factor_rotation=factor_q,
                        ticker=info['ticker'], company_name=info['name'],
                        coverage='verified-membership')
        # Keep signals visible even when their company-membership source is empty.
        for (kind, sid), (label, source_q) in source.items():
            if (kind, sid) in populated_sources:
                continue
            add(rotation=q, country=country,
                sector=label if kind == 'sector' else '',
                factor=label if kind == 'factor' else '', scope=scope,
                sector_id=f'{scope}:sector:{sid}' if kind == 'sector' else '',
                factor_id=f'{scope}:factor:{sid}' if kind == 'factor' else '',
                sector_rotation=source_q if kind == 'sector' else '',
                factor_rotation=source_q if kind == 'factor' else '',
                coverage='signal-without-company')
        diagnostics[f'{region}_companies'] = len(by_company)
    return pd.DataFrame(records), diagnostics


def filter_table(table: pd.DataFrame, rotations=(), countries=(), sectors=(),
                 companies=(), factors=(), mode='Any selected') -> pd.DataFrame:
    """Cross-dimension AND. Multiple selections within each dimension OR.

    Sector/factor ALL means the same company is connected to every selected
    sector/factor, possibly via different valid rows; it does not require one
    impossible single row to hold multiple values.
    """
    df = table.copy()
    for col, values in [('Rotation', rotations), ('Country', countries)]:
        if values:
            df = df[df[col].isin(values)]
    if companies:
        df = df[df['company_id'].isin(companies)]
    selected_sets = []
    for val in sectors:
        selected_sets.append(set(df.loc[df['sector_id'] == val, 'company_id']) - {''})
    for val in factors:
        selected_sets.append(set(df.loc[df['factor_id'] == val, 'company_id']) - {''})
    if selected_sets:
        matches = (set.intersection(*selected_sets) if mode == 'All selected'
                   else set.union(*selected_sets))
        df = df[df['company_id'].isin(matches)]
        # Keep every *verified* membership for matching companies. This allows
        # tracing selected sectors through companies to their other factors.
    return df


def make_graph(table: pd.DataFrame, show_country_only=True):
    """Strict adjacent-column edges from one canonical table; no skipped columns."""
    nodes = {'root': {'label': 'GLOBAL', 'kind': 'Global', 'rotation': ''}}
    edges = set()
    for row in table.to_dict('records'):
        rot = row['Rotation']
        country = row['Country']
        scope = row['scope']
        if not rot or not country:
            continue
        rid = f'rotation:{rot}'
        coid = f'country:{scope}'
        nodes[rid] = {'label': rot, 'kind': 'Rotation', 'rotation': rot}
        nodes[coid] = {'label': country, 'kind': 'Country', 'rotation': rot}
        edges.add(('root', rid))
        edges.add((rid, coid))
        if row['sector_id']:
            sid = row['sector_id']
            nodes[sid] = {'label': row['Sector'], 'kind': 'Sector',
                          'rotation': row['sector_rotation'], 'scope': scope}
            edges.add((coid, sid))
        if row['company_id']:
            cid = row['company_id']
            nodes[cid] = {'label': row['Company'], 'kind': 'Company', 'rotation': rot,
                          'scope': scope, 'name': row['company_name']}
            if row['sector_id']:
                edges.add((row['sector_id'], cid))
            # A factor-only company has no *verified* sector; it appears as
            # a node but we intentionally do not invent Country -> Sector -> Company.
        if row['factor_id']:
            fid = row['factor_id']
            nodes[fid] = {'label': row['Factor'], 'kind': 'Factor',
                          'rotation': row['factor_rotation'], 'scope': scope}
            if row['company_id']:
                edges.add((row['company_id'], fid))
            # Factor nodes with no company evidence remain unconnected.
    return nodes, sorted(edges)


def plot_network(nodes: dict, edges: list, height=720):
    kinds = ('Global', 'Rotation', 'Country', 'Sector', 'Company', 'Factor')
    groups = [[nid for nid, n in nodes.items() if n['kind'] == k] for k in kinds]
    for group in groups:
        group.sort(key=lambda n: (nodes[n].get('scope', ''), nodes[n]['label'].casefold(), n))
    pos = {nid: (i, 1 - (j + .5) / max(1, len(group)))
           for i, group in enumerate(groups) for j, nid in enumerate(group)}
    fig = go.Figure()
    # Every displayed edge joins *adjacent* columns, at a consistent line width.
    for q in (*ROTATIONS, 'Unclassified', 'Global scope'):
        xs, ys = [], []
        for a, b in edges:
            color_group = (nodes[b].get('rotation') if nodes[b]['kind'] == 'Country'
                           else nodes[a].get('rotation') if nodes[a]['kind'] == 'Rotation'
                           else '')
            if color_group != q:
                continue
            xs += [pos[a][0], pos[b][0], None]
            ys += [pos[a][1], pos[b][1], None]
        if xs:
            fig.add_trace(go.Scattergl(x=xs, y=ys, mode='lines', hoverinfo='skip',
                                      line=dict(color=COLORS[q], width=1.7),
                                      opacity=.76, showlegend=False))
    # Sector->company and company->factor edges have no country rotation on
    # those endpoints; draw them at the SAME visual weight as other edges.
    xs, ys = [], []
    for a, b in edges:
        if nodes[a]['kind'] in ('Rotation', 'Global'):
            continue
        if nodes[b]['kind'] == 'Country':
            continue
        xs += [pos[a][0], pos[b][0], None]
        ys += [pos[a][1], pos[b][1], None]
    if xs:
        fig.add_trace(go.Scattergl(x=xs, y=ys, mode='lines', hoverinfo='skip',
                                  line=dict(color='#7194a9', width=1.7),
                                  opacity=.42, showlegend=False))
    for i, group in enumerate(groups):
        if not group:
            continue
        fig.add_trace(go.Scattergl(
            x=[pos[n][0] for n in group], y=[pos[n][1] for n in group],
            mode='markers+text',
            marker=dict(size=10 if i not in (0, 4) else 8,
                        color=[COLORS.get(nodes[n].get('rotation'), '#8cd7c8') for n in group]),
            text=[nodes[n]['label'] if i != 4 or len(group) <= 28 else '' for n in group],
            textposition='middle right', textfont=dict(size=10, color='#e5edf7'),
            hovertext=[f"{nodes[n]['label']}<br>{nodes[n]['kind']}<br>Scope: {nodes[n].get('scope', '')}"
                       for n in group], hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False))
    for i, k in enumerate(kinds):
        fig.add_annotation(x=i, y=1.065, text=f'<b>{k.upper()}</b>', showarrow=False,
                           font=dict(size=12, color='#e5edf7'))
    fig.update_layout(height=height, paper_bgcolor='#101b2b', plot_bgcolor='#101b2b',
                      margin=dict(l=60, r=100, t=65, b=30),
                      xaxis=dict(visible=False, range=[-.3, 5.5]),
                      yaxis=dict(visible=False, range=[-.06, 1.12]),
                      showlegend=False, dragmode='pan')
    return fig


def render_capital_network():
    st.title('Global Capital Intelligence Network')
    st.caption('One verified relationship table · GLOBAL → ROTATION → COUNTRY → SECTOR → COMPANY → FACTOR')
    period = st.radio('Lookback', ('1m', '3m', '6m'), index=1, horizontal=True, key='cap_period_table')
    table, diagnostics = build_capital_table(period)
    if table.empty:
        st.error('No capital network records available. Check the graph cache files.')
        st.json(diagnostics)
        return
    st.info('Country-specific company evidence is currently available for USA and India. '
            'Other tracked countries remain visible but cannot be connected to sectors or '
            'companies until country-scoped memberships are collected. Global direct is a scope, not a country.')
    if diagnostics['classified_countries'] < diagnostics['tracked_countries']:
        st.warning(f"Country classifications: {diagnostics['classified_countries']}/{diagnostics['tracked_countries']}. "
                   'Missing classifications are shown as Unclassified.')
    view = st.radio('View', ('Overview', 'Sector / Factor', 'Individual Companies'),
                    horizontal=True, key='cap_view_table')
    def options(col, idcol=None):
        if idcol is None:
            return sorted(x for x in table[col].unique() if x)
        entries = table[[col, idcol, 'scope']].drop_duplicates()
        return {f'{r[col]} [{r["scope"]} · {r[idcol].split(":")[-1]}]': r[idcol]
                for r in entries.to_dict('records') if r[col] and r[idcol]}
    sector_options = options('Sector', 'sector_id')
    factor_options = options('Factor', 'factor_id')
    company_options = options('Company', 'company_id')
    with st.expander('Filters — multi-select', expanded=(view != 'Overview')):
        a, b, c = st.columns(3)
        with a:
            rotations = st.multiselect('Rotations', options('Rotation'), key='cap_rotation_table')
            countries = st.multiselect('Countries / Global direct', options('Country'), key='cap_country_table')
        with b:
            sectors = st.multiselect('Sectors', list(sector_options), key='cap_sector_table')
            factors = st.multiselect('Factors', list(factor_options), key='cap_factor_table')
        with c:
            companies = st.multiselect('Companies', list(company_options), key='cap_company_table')
            match = st.radio('Sector/factor matching', ('Any selected', 'All selected'),
                             horizontal=True, key='cap_match_table')
    filtered = filter_table(table, rotations, countries,
                            [sector_options[x] for x in sectors],
                            [company_options[x] for x in companies],
                            [factor_options[x] for x in factors], mode=match)
    total = filtered.loc[filtered['company_id'].ne(''), 'company_id'].nunique()
    show_all = st.checkbox('Show all matching companies (may be slow)', key='cap_show_all_table')
    limit = None if show_all else (45 if view == 'Overview' else 90)
    if limit is not None and total > limit:
        keep = sorted(filtered.loc[filtered['company_id'].ne(''), 'company_id'].unique())[:limit]
        filtered = filtered[filtered['company_id'].isin(keep) |
                            ((filtered['company_id'] == '') &
                             (filtered['Sector'] == '') & (filtered['Factor'] == ''))]
    # If a filter is active, no unrelated country-only rows remain.
    active = any((rotations, countries, sectors, factors, companies))
    if active and filtered.empty:
        st.warning('No verified paths match these filters.')
        return
    nodes, edges = make_graph(filtered)
    st.caption(f'{len(nodes):,} nodes · {len(edges):,} verified adjacent-column links · '
               f'{total:,} matching companies ({min(total, limit) if limit else total:,} shown)')
    st.plotly_chart(plot_network(nodes, edges), use_container_width=True,
                    config={'scrollZoom': True, 'displaylogo': False})
    with st.expander('Canonical Global / Rotation / Country / Sector / Company / Factor table'):
        st.dataframe(filtered[list(COLS) + ['sector_rotation', 'factor_rotation', 'coverage']],
                     use_container_width=True, hide_index=True)
        st.download_button('Download complete backend table (CSV)',
                           data=table.to_csv(index=False).encode('utf-8'),
                           file_name=f'capital_network_{period}_complete.csv', mime='text/csv')
    if any(x.endswith(('signals', 'edges')) for x in diagnostics):
        with st.expander('Data coverage diagnostics'):
            st.json(diagnostics)
