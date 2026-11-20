"""Regional four-quadrant rotation knowledge graphs from materialized snapshots.

Hierarchy: rotation quadrant -> sector/factor index -> constituent company.
Edges denote mapped index membership, not capital flows or stock-price signals.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs'
QUADRANTS = ('Leading', 'Improving', 'Weakening', 'Lagging')
COLORS = {'Leading':'#38d9a9', 'Improving':'#60a5fa', 'Weakening':'#fbbf24', 'Lagging':'#fb7185',
          'sector':'#b3e5fc', 'factor':'#c4b5fd', 'company':'#e5e7eb'}


@st.cache_data(show_spinner=False, max_entries=48)
def _read_csv(filename: str, mtime: int) -> pd.DataFrame:
    try:
        return pd.read_csv(filename, keep_default_na=False)
    except (FileNotFoundError, OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _load(region: str, period: str, kind: str) -> pd.DataFrame:
    path = STORE / f'{region.lower()}_{period}_{kind}.csv'
    return _read_csv(str(path), path.stat().st_mtime_ns if path.is_file() else -1)


def _manifest() -> dict:
    try:
        return json.loads((STORE / 'manifest.json').read_text(encoding='utf8'))
    except (OSError, ValueError):
        return {}


def _sources(value) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [s.strip() for s in str(value).split(' · ') if s.strip()]


def graph_elements(companies: pd.DataFrame, signals: pd.DataFrame, quadrant: str, limit: int):
    """Return graph nodes/links; source membership is supported by company snapshot.

    A source must match a uniquely identified index name, kind and quadrant. This
    prevents a proxy name from being linked to a different signal by accident.
    """
    if quadrant not in QUADRANTS:
        raise ValueError(f'Unknown quadrant: {quadrant}')
    if companies.empty or signals.empty:
        return [], []
    required = {'Category', 'Company', 'Ticker', 'company_key', 'Score', 'Sector sources', 'Factor sources'}
    signal_fields = {'kind', 'label', 'quadrant'}
    if not required.issubset(companies.columns) or not signal_fields.issubset(signals.columns):
        return [], []
    subset = companies.loc[companies['Category'].eq(quadrant)].copy()
    subset['Score'] = pd.to_numeric(subset['Score'], errors='coerce')
    subset = subset.dropna(subset=['Score']).sort_values('Score', ascending=False).head(limit)
    matched = signals.loc[signals['quadrant'].eq(quadrant)]
    labels = {(kind, label) for (kind, label), grp in matched.groupby(['kind', 'label']) if len(grp) == 1}

    nodes = [{'id':f'q:{quadrant}', 'label':quadrant, 'type':'rotation', 'quadrant':quadrant}]
    links = []
    seen = {nodes[0]['id']}
    for row in subset.to_dict('records'):
        sources = []
        for kind, column in (('sector', 'Sector sources'), ('factor', 'Factor sources')):
            for label in _sources(row[column]):
                if (kind, label) in labels:
                    sources.append((kind, label))
        # Only show companies with evidence from both sector AND factor branches.
        if not {'sector', 'factor'}.issubset({kind for kind, _ in sources}):
            continue
        company_id = f"c:{str(row['company_key'])}"
        if company_id not in seen:
            nodes.append({'id':company_id, 'label':str(row['Ticker']) or str(row['Company']),
                          'name':str(row['Company']), 'type':'company', 'score':float(row['Score']),
                          'quadrant':quadrant})
            seen.add(company_id)
        for kind, label in sorted(set(sources)):
            idx_id = f'i:{kind}:{label}'
            if idx_id not in seen:
                sig = matched.loc[matched['kind'].eq(kind) & matched['label'].eq(label)].iloc[0]
                nodes.append({'id':idx_id, 'label':label, 'type':kind,
                              'rs':sig.get('relative_strength', ''), 'momentum':sig.get('rs_momentum', ''),
                              'quadrant':quadrant})
                links.append((f'q:{quadrant}', idx_id))
                seen.add(idx_id)
            links.append((idx_id, company_id))
    return nodes, list(dict.fromkeys(links))


def combined_graph_elements(companies: pd.DataFrame, signals: pd.DataFrame,
                            quadrants: tuple[str, ...], limit: int):
    """Keep independent category lanes; do not merge identical index/company labels
    across categories because their rotation evidence may differ.
    """
    nodes, links = [], []
    for quadrant in quadrants:
        lane_nodes, lane_links = graph_elements(companies, signals, quadrant, limit)
        # Prefix non-rotation IDs to prevent accidentally merging signals shared by lanes.
        def scoped(node_id):
            return node_id if node_id.startswith('q:') else f'{quadrant}|{node_id}'
        for node in lane_nodes:
            nodes.append({**node, 'id': scoped(node['id'])})
        links.extend((scoped(a), scoped(b)) for a, b in lane_links)
    return nodes, links


def _plot(nodes, links, quadrants):
    """Left-to-right, three-column Sankey-style knowledge graph.

    Left: four rotation quadrants; center: sector and factor nodes; right:
    company nodes. Each category has its own horizontal lane.
    """
    if not links:
        st.info('No companies currently have verified sector AND factor evidence in the selected rotation categories.')
        return

    by_id = {node['id']: node for node in nodes}
    by_lane = {q: {'rotation': [], 'sector': [], 'factor': [], 'company': []}
               for q in quadrants}
    for node in nodes:
        q = node.get('quadrant')
        if q in by_lane:
            by_lane[q][node['type']].append(node)

    positions = {}
    lane_bounds = {}
    top = 0.0
    for quadrant in quadrants:
        groups = by_lane[quadrant]
        sectors = sorted(groups['sector'], key=lambda n: n['label'])
        factors = sorted(groups['factor'], key=lambda n: n['label'])
        companies = sorted(groups['company'], key=lambda n: n['label'])
        # Allow space for the entire center column and for all company labels.
        lane_height = max(6.0, (len(sectors) + len(factors)) * 1.12 + 2.0,
                          len(companies) * 0.95 + 2.0)
        center_y = top - lane_height / 2
        lane_bounds[quadrant] = (top, top - lane_height, center_y)
        positions[f'q:{quadrant}'] = (0.0, center_y)
        middle = sectors + factors
        for idx, node in enumerate(middle):
            y = center_y + (len(middle) - 1) * 0.56 - idx * 1.12
            positions[node['id']] = (1.38, y)
        for idx, node in enumerate(companies):
            y = center_y + (len(companies) - 1) * 0.475 - idx * 0.95
            positions[node['id']] = (2.85, y)
        top -= lane_height + 1.4

    fig = go.Figure()
    for quadrant in quadrants:
        lane_links = [(a, b) for a, b in links if by_id[a]['quadrant'] == quadrant]
        # Draw link traces by lane, colored by rotation category.
        xvals, yvals = [], []
        for source, target in lane_links:
            if source not in positions or target not in positions:
                continue
            a, b = positions[source], positions[target]
            xvals.extend([a[0], b[0], None])
            yvals.extend([a[1], b[1], None])
        fig.add_trace(go.Scatter(
            x=xvals, y=yvals, mode='lines',
            line={'color': COLORS[quadrant], 'width': 1}, opacity=0.32,
            hoverinfo='skip', showlegend=False))

    for kind in ('rotation', 'sector', 'factor', 'company'):
        group = [node for node in nodes if node['type'] == kind and node['id'] in positions]
        if not group:
            continue
        hover = []
        for node in group:
            q = node['quadrant']
            if kind in ('sector', 'factor'):
                hover.append(f"{q} · {kind.title()}: {node['label']}<br>RS: {node.get('rs')}<br>RS momentum: {node.get('momentum')}")
            elif kind == 'company':
                hover.append(f"{q} · {node.get('name', node['label'])}<br>Evidence score: {node.get('score')}")
            else:
                hover.append(f'{q} rotation')
        fig.add_trace(go.Scatter(
            x=[positions[n['id']][0] for n in group],
            y=[positions[n['id']][1] for n in group],
            mode='markers+text',
            marker={'size': 30 if kind == 'rotation' else 16 if kind != 'company' else 18,
                    'color': [COLORS[n['quadrant']] if kind == 'rotation' else COLORS[kind]
                              for n in group],
                    'line': {'width': 1, 'color': '#101827'}},
            text=[n['label'][:23] for n in group],
            textposition='top center', textfont={'size': 10, 'color': '#e5edf7'},
            hovertext=hover, hovertemplate='%{hovertext}<extra></extra>',
            name=kind.title()))

    for q in quadrants:
        upper, lower, center = lane_bounds[q]
        fig.add_hline(y=lower - 0.65, line_color='rgba(180,200,220,0.18)', line_width=1)
        fig.add_annotation(x=-0.17, y=upper - 0.3, text=q.upper(), showarrow=False,
                           xanchor='left', font={'size': 11, 'color': COLORS[q]})

    for x, label in ((0, 'ROTATION'), (1.38, 'SECTORS / FACTORS'), (2.85, 'COMPANIES')):
        fig.add_annotation(x=x, y=1.2, text=f'<b>{label}</b>', showarrow=False,
                           font={'size': 14, 'color': '#e5edf7'})
    total_height = sum(upper - lower for upper, lower, _ in lane_bounds.values())
    height = max(650, min(2400, int(total_height * 25 + 200)))
    fig.update_layout(
        height=height, paper_bgcolor='#101827', plot_bgcolor='#101827',
        font={'color': '#e5edf7'}, margin={'l': 60, 'r': 90, 't': 60, 'b': 35},
        xaxis={'visible': False, 'range': [-0.35, 3.22]},
        yaxis={'visible': False, 'range': [top - 0.4, 2.6]},
        hovermode='closest', showlegend=True, legend={'orientation': 'h'},
        dragmode='pan')
    st.plotly_chart(fig, use_container_width=True,
                    config={'scrollZoom': True, 'displaylogo': False})


def render_graph(region: str):
    if region not in ('Global','USA','India'):
        st.error('Unsupported region'); return
    st.title(f'{region} Rotation Knowledge Graph')
    st.caption('LEFT: Leading / Improving / Weakening / Lagging → MIDDLE: sectors & factors → RIGHT: companies. Lines represent verified membership, not fund flows.')
    left, middle, right = st.columns(3)
    period = left.selectbox('Lookback', ['1m','3m','6m'], index=1, key=f'kg_period_{region}')
    selection = middle.selectbox('Rotation category', ('All four', *QUADRANTS), key=f'kg_quadrant_{region}')
    quadrants = QUADRANTS if selection == 'All four' else (selection,)
    limit = right.slider('Maximum companies', 5, 50, 15, 5, key=f'kg_count_{region}')
    companies, signals = _load(region,period,'companies'), _load(region,period,'signals')
    status = _manifest().get('regions',{}).get(f'{region.lower()}_{period}',{})
    if signals.empty:
        st.warning('No verified market rotation snapshot exists. Run the regional graph builder after the price/holdings refresh.')
        if status.get('error'): st.error(str(status['error']))
        return
    counts = [len(companies.loc[companies['Category'].eq(q)]) if 'Category' in companies.columns else 0 for q in QUADRANTS]
    for col, q, count in zip(st.columns(4), QUADRANTS, counts):
        col.metric(f'{q} companies',count)
    if status.get('signal_asof'): st.caption(f"Market signals as of {status['signal_asof']}")
    nodes, links = combined_graph_elements(companies, signals, quadrants, limit)
    _plot(nodes, links, quadrants)
    with st.expander('Underlying sector & factor signals'):
        cols = [c for c in ('kind','label','quadrant','relative_strength','rs_momentum','as_of') if c in signals.columns]
        st.dataframe(signals.loc[signals.quadrant.isin(quadrants),cols], hide_index=True, use_container_width=True)
    with st.expander('Company evidence table'):
        if not companies.empty and 'Category' in companies.columns:
            st.dataframe(companies.loc[companies.Category.isin(quadrants)], hide_index=True, use_container_width=True)
    st.info('Market rotation is index-level and benchmark-relative. Company links represent holdings or index membership; they do not measure each stock’s rotation or capital inflows.')
