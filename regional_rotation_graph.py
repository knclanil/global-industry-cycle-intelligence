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
    """Create ONE network: four rotation nodes, shared center, unique companies.

    Index evidence stays quadrant-scoped. Company IDs are shared so a company
    connected to several qualifying sector/factor indexes is drawn only once.
    """
    nodes, links = [], []
    seen = set()
    for quadrant in quadrants:
        lane_nodes, lane_links = graph_elements(companies, signals, quadrant, limit)

        def scoped(node_id):
            if node_id.startswith(('q:', 'c:')):
                return node_id
            return f'{quadrant}|{node_id}'

        for node in lane_nodes:
            new_id = scoped(node['id'])
            if new_id not in seen:
                nodes.append({**node, 'id': new_id})
                seen.add(new_id)
        links.extend((scoped(a), scoped(b)) for a, b in lane_links)

    # The rotation nodes are always present, including for quadrants with no
    # qualifying company links, so the user always sees exactly four endpoints.
    for quadrant in quadrants:
        node_id = f'q:{quadrant}'
        if node_id not in seen:
            nodes.append({'id': node_id, 'label': quadrant,
                          'type': 'rotation', 'quadrant': quadrant})
            seen.add(node_id)
    return nodes, list(dict.fromkeys(links))


def _plot(nodes, links, quadrants):
    """Render ONE three-column network, not four vertically separated charts.

    Left: exactly four rotation nodes. Middle: all sector/factor nodes.
    Right: unique companies. Each edge shows one observed membership relation.
    """
    by_id = {node['id']: node for node in nodes}
    order = {quadrant: i for i, quadrant in enumerate(QUADRANTS)}

    rotations = [by_id[f'q:{q}'] for q in quadrants if f'q:{q}' in by_id]
    indices = sorted(
        (n for n in nodes if n['type'] in ('sector', 'factor')),
        key=lambda n: (order.get(n['quadrant'], 99),
                       0 if n['type'] == 'sector' else 1, n['label'].lower()))
    companies = sorted(
        (n for n in nodes if n['type'] == 'company'),
        key=lambda n: (order.get(n['quadrant'], 99), n['label'].lower()))

    # All nodes are placed in the SAME coordinate system; no per-quadrant
    # subplots, separator lines or independently scaled panes.
    positions = {}
    for i, q in enumerate(quadrants):
        positions[f'q:{q}'] = (0.0, 1 - (i + 0.5) / len(quadrants))
    for group, x in ((indices, 1.28), (companies, 2.63)):
        for i, node in enumerate(group):
            positions[node['id']] = (x, 1 - (i + 0.5) / max(len(group), 1))

    fig = go.Figure()
    for quadrant in quadrants:
        xvals, yvals = [], []
        for source, target in links:
            # Sector/factor node provenance determines the edge color.
            center = by_id.get(source if '|i:' in source else target)
            if not center or center.get('quadrant') != quadrant:
                continue
            if source not in positions or target not in positions:
                continue
            start, end = positions[source], positions[target]
            xvals.extend([start[0], end[0], None])
            yvals.extend([start[1], end[1], None])
        if xvals:
            fig.add_trace(go.Scatter(
                x=xvals, y=yvals, mode='lines',
                line={'color': COLORS[quadrant], 'width': 1.1}, opacity=0.27,
                hoverinfo='skip', name=quadrant, showlegend=False))

    for kind, group in (('rotation', rotations), ('sector', [n for n in indices if n['type'] == 'sector']),
                        ('factor', [n for n in indices if n['type'] == 'factor']),
                        ('company', companies)):
        if not group:
            continue
        hover = []
        for node in group:
            q = node['quadrant']
            if kind in ('sector', 'factor'):
                hover.append(f"{q} · {kind.title()}: {node['label']}<br>RS: {node.get('rs')}<br>RS momentum: {node.get('momentum')}")
            elif kind == 'company':
                hover.append(f"{node.get('name', node['label'])}<br>Evidence score: {node.get('score')}")
            else:
                hover.append(f'{q} rotation')
        fig.add_trace(go.Scatter(
            x=[positions[n['id']][0] for n in group],
            y=[positions[n['id']][1] for n in group],
            mode='markers+text',
            marker={'size': 27 if kind == 'rotation' else 12 if kind != 'company' else 10,
                    'symbol': 'diamond' if kind == 'factor' else 'circle',
                    'color': [COLORS[n['quadrant']] if kind == 'rotation' else COLORS[kind]
                              for n in group],
                    'line': {'width': 1, 'color': '#101827'}},
            text=[n['label'] if kind == 'rotation' else n['label'][:25] for n in group],
            textposition='middle left' if kind == 'rotation' else 'middle right',
            textfont={'size': 11 if kind == 'rotation' else 9, 'color': '#e5edf7'},
            hovertext=hover, hovertemplate='%{hovertext}<extra></extra>',
            name=kind.title()))

    for x, label in ((0, 'ROTATIONS'), (1.28, 'SECTORS / FACTORS'), (2.63, 'COMPANIES')):
        fig.add_annotation(x=x, y=1.045, text=f'<b>{label}</b>', showarrow=False,
                           xanchor='center', font={'size': 13, 'color': '#e5edf7'})
    fig.update_layout(
        height=max(680, min(2200, max(len(indices), len(companies)) * 28 + 130)),
        paper_bgcolor='#101827', plot_bgcolor='#101827',
        font={'color': '#e5edf7'}, margin={'l': 95, 'r': 145, 't': 70, 'b': 30},
        xaxis={'visible': False, 'range': [-0.37, 3.08], 'fixedrange': True},
        yaxis={'visible': False, 'range': [-0.03, 1.10], 'fixedrange': False},
        hovermode='closest', showlegend=True, legend={'orientation': 'h'},
        dragmode='pan')
    st.plotly_chart(fig, use_container_width=True,
                    config={'scrollZoom': True, 'displaylogo': False})
    if not links:
        st.info('No company links meet the verified sector AND factor rule for the selected lookback. All four rotations remain visible.')


def render_graph(region: str):
    if region not in ('Global','USA','India'):
        st.error('Unsupported region'); return
    st.title(f'{region} Rotation Knowledge Graph')
    st.caption('LEFT: Leading / Improving / Weakening / Lagging → MIDDLE: sectors & factors → RIGHT: companies. Lines represent verified membership, not fund flows.')
    left, middle, right = st.columns(3)
    period = left.selectbox('Lookback', ['1m','3m','6m'], index=1, key=f'kg_period_{region}')
    middle.caption('One unified network · all four rotations')
    quadrants = QUADRANTS
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
