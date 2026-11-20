"""One unified rotation -> sectors/factors -> companies graph, for 3 regions.

All four classifications and all verified membership links are shown by default.
No AND-filter between sector and factor membership; no top-N truncation.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from rotation_graph_evidence import QUADRANTS, graph_elements

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs'
COLORS = {'Leading':'#38d9a9','Improving':'#60a5fa',
          'Weakening':'#fbbf24','Lagging':'#fb7185',
          'sector':'#b3e5fc','factor':'#c4b5fd','company':'#e5e7eb'}

@st.cache_data(show_spinner=False, max_entries=48)
def _read_csv(filename: str, mtime: int):
    try:
        return pd.read_csv(filename, keep_default_na=False)
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _load(region, period, kind):
    file = STORE / f'{region.lower()}_{period}_{kind}.csv'
    return _read_csv(str(file), file.stat().st_mtime_ns if file.is_file() else -1)


def _manifest():
    try:
        return json.loads((STORE / 'manifest.json').read_text(encoding='utf8'))
    except (OSError, ValueError):
        return {}


def plot_network(nodes, links):
    by_id = {n['id']: n for n in nodes}
    q_order = {q: k for k, q in enumerate(QUADRANTS)}
    indices = sorted((n for n in nodes if n['type'] in ('sector','factor')),
                     key=lambda n: (q_order[n['quadrant']], n['type'], n['label'].lower()))
    companies = sorted((n for n in nodes if n['type'] == 'company'),
                       key=lambda n: n['label'].lower())
    positions = {f'q:{q}': (0.0, 1 - (i + .5) / 4) for i, q in enumerate(QUADRANTS)}
    for group, x in ((indices, 1.2), (companies, 2.55)):
        for i, n in enumerate(group):
            positions[n['id']] = (x, 1 - (i + .5) / max(1, len(group)))

    fig = go.Figure()
    for quadrant in QUADRANTS:
        xs, ys = [], []
        for a, b in links:
            if a not in positions or b not in positions:
                continue
            center = by_id.get(a if a.startswith('i:') else b)
            if not center or center.get('quadrant') != quadrant:
                continue
            p1, p2 = positions[a], positions[b]
            xs.extend([p1[0], p2[0], None])
            ys.extend([p1[1], p2[1], None])
        if xs:
            fig.add_trace(go.Scattergl(x=xs, y=ys, mode='lines',
                        line={'color':COLORS[quadrant], 'width':1}, opacity=.20,
                        hoverinfo='skip', showlegend=False))

    for kind, group in (
        ('rotation',[by_id[f'q:{q}'] for q in QUADRANTS]),
        ('sector',[n for n in indices if n['type']=='sector']),
        ('factor',[n for n in indices if n['type']=='factor']),
        ('company',companies),
    ):
        if not group:
            continue
        tooltips = []
        for n in group:
            if kind == 'rotation':
                tip = f"<b>{n['label']}</b>"
            elif kind == 'company':
                tip = f"<b>{n.get('name') or n['label']}</b><br>Identifier: {n['company_key']}"
            else:
                tip = (f"<b>{n['label']}</b> ({kind})<br>Quadrant: {n['quadrant']}"
                       f"<br>Relative strength: {n.get('rs', 'N/A')}"
                       f"<br>RS momentum: {n.get('momentum', 'N/A')}")
            tooltips.append(tip)
        fig.add_trace(go.Scattergl(
            x=[positions[n['id']][0] for n in group],
            y=[positions[n['id']][1] for n in group],
            mode='markers+text',
            marker={'size':23 if kind=='rotation' else 10 if kind!='company' else 6,
                    'color':[COLORS[n['quadrant']] if kind=='rotation' else COLORS[kind] for n in group],
                    'symbol':'diamond' if kind=='factor' else 'circle'},
            text=[n['label'] if kind!='company' else n['label'] for n in group],
            textposition='middle left' if kind=='rotation' else 'middle right',
            textfont={'size':11 if kind=='rotation' else 9,'color':'#e5edf7'},
            hovertext=tooltips, hovertemplate='%{hovertext}<extra></extra>',
            name=kind.title()))
    for x, caption in ((0,'ROTATIONS'),(1.2,'SECTORS / FACTORS'),(2.55,'COMPANIES')):
        fig.add_annotation(x=x, y=1.045, text=f'<b>{caption}</b>',
                           showarrow=False, font={'color':'#e5edf7','size':12})
    # The full graph can be tall: allow scroll rather than hiding company nodes.
    fig.update_layout(height=max(700, min(6500, max(len(indices),len(companies))*20+160)),
        paper_bgcolor='#101827', plot_bgcolor='#101827',
        margin={'l':110,'r':135,'t':75,'b':25},
        xaxis={'visible':False,'range':[-.4,3.0],'fixedrange':True},
        yaxis={'visible':False,'range':[-.03,1.10]},
        font={'color':'#e5edf7'}, legend={'orientation':'h'},
        hovermode='closest', dragmode='pan')
    st.plotly_chart(fig, use_container_width=True,
                    config={'scrollZoom':True, 'displaylogo':False})


def render_graph(region: str):
    if region not in ('Global','USA','India'):
        st.error('Unsupported region'); return
    st.title(f'{region} Rotation Knowledge Graph')
    st.caption('ONE network: four rotations → ALL available sectors/factors → ALL companies with verified membership. An edge is not a stock-price rotation signal.')
    period = st.selectbox('Lookback', ['1m','3m','6m'], index=1,
                          key=f'kg_period_{region}')
    signals = _load(region,period,'signals')
    edges = _load(region,period,'edges')
    status = _manifest().get('regions',{}).get(f'{region.lower()}_{period}',{})
    if signals.empty:
        st.warning('No market signals available. Refresh source price data and run scripts/build_regional_rotation_graphs.py.')
        if status.get('error'):
            st.error(str(status['error']))
        return
    if not (STORE / f'{region.lower()}_{period}_edges.csv').is_file():
        st.error('Graph membership snapshot is missing. Deploy the updated builder and regenerate the caches; the old *_companies.csv is NOT a complete graph source.')
        return
    if status.get('error'):
        st.warning(f"Latest cache build issue: {status['error']}")
    counts = []
    for q in QUADRANTS:
        count_signals = int(signals['quadrant'].eq(q).sum()) if 'quadrant' in signals else 0
        count_companies = int(edges.loc[edges.quadrant.eq(q),'company_key'].nunique()) if not edges.empty else 0
        counts.append((count_signals,count_companies))
    for col, q, (s_count,c_count) in zip(st.columns(4),QUADRANTS,counts):
        col.metric(q, f'{s_count} indices', f'{c_count} mapped companies', delta_color='off')
    if status.get('signal_asof'):
        st.caption(f"Market signals as of: {status['signal_asof']}")
    nodes,links = graph_elements(signals,edges)
    st.caption(f"Complete view: {len(nodes):,} nodes, {len(links):,} unique relationships. No top-N exclusion.")
    plot_network(nodes,links)
    if any(s_count==0 for s_count,_ in counts):
        st.warning('A category has no valid index signal in this data snapshot; its rotation node is shown without invented sector/factor connections.')
    if edges.empty:
        st.warning('No verified company memberships were mapped. All available sector/factor signals remain visible; inspect the unmapped-source report.')
    with st.expander('All sector and factor signals'):
        st.dataframe(signals, use_container_width=True,hide_index=True)
    with st.expander('All verified company membership connections'):
        st.dataframe(edges, use_container_width=True,hide_index=True)
    with st.expander('Unmapped holdings sources'):
        st.dataframe(_load(region,period,'unmapped'),use_container_width=True,hide_index=True)
    st.info('Classification is benchmark-relative at the sector/factor index level. Company links reflect portfolio holdings or index constituents, not independent stock rotation or capital flows.')
