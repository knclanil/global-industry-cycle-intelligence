"""Global Capital Intelligence Network: six linked, evidence-first columns.

Drop-in replacement retaining the application's render_capital_network() API.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from capital_network_model import (build_model, global_breadth_score,
    filter_model, to_graph, validate_model, ROTATIONS, ROUTE)

CACHE = Path(__file__).resolve().parent / 'data/dashboard_cache/rotation_graphs'
COLORS = {'Leading':'#31d4a1','Improving':'#62a9ff',
          'Weakening':'#ffc44d','Lagging':'#f17692',
          'Unclassified':'#aab6c8','Global scope':'#b795fa'}


def plot_model(nodes, edges, height=690):
    layers = {i: [] for i in range(6)}
    for nid, n in nodes.items():
        layers[n['layer']].append(nid)
    for i in layers:
        layers[i].sort(key=lambda nid:(nodes[nid].get('scope',''),
                                        nodes[nid]['label'].casefold(),nid))
    positions = {nid:(i, 1-(index+.5)/max(1,len(group)))
                 for i,group in layers.items() for index,nid in enumerate(group)}
    fig = go.Figure()
    # Uniform width for every verified relationship; gaps dashed and subdued.
    for category in (*ROTATIONS,'Unclassified','Global scope','neutral','unverified'):
        xs,ys=[],[]
        for e in edges:
            a,b=e['source'],e['target']
            if not e['verified']:
                group='unverified'
            elif nodes[a]['layer'] <= 1:
                group=(nodes[b]['rotation'] if nodes[b]['layer']==2
                       else nodes[b]['label'])
            else:
                group='neutral'
            if group!=category:
                continue
            xs.extend([positions[a][0], positions[b][0], None])
            ys.extend([positions[a][1], positions[b][1], None])
        if xs:
            fig.add_trace(go.Scattergl(x=xs,y=ys,mode='lines',hoverinfo='skip',
                line=dict(color=COLORS.get(category,'#647d93'),
                          width=1.5, dash='dash' if category=='unverified' else 'solid'),
                opacity=.34 if category=='neutral' else .75,
                showlegend=False))
    for i,ids in layers.items():
        if not ids: continue
        labels=[nodes[n]['label'] for n in ids]
        # Show company tickers on focused sets; hide only in dense overview.
        display=[label if i!=4 or len(ids)<=55 else '' for label in labels]
        hover=[]
        for nid in ids:
            n=nodes[nid]
            pieces=[n['kind'],n['label']]
            for k,label in [('full_name','Company name'),('rs','Relative strength (%)'),
                            ('momentum','Momentum (pp)'),('as_of','As of')]:
                if n.get(k): pieces.append(f'{label}: {n[k]}')
            if n['kind']=='Gap': pieces.append('Dashed edges are NOT verified memberships')
            hover.append('<br>'.join(pieces))
        fig.add_trace(go.Scattergl(x=[positions[n][0] for n in ids],
            y=[positions[n][1] for n in ids],mode='markers+text',
            marker=dict(size=11 if i in (0,1,2) else 8,
                        color=[COLORS.get(nodes[n].get('rotation'),
                               '#e6ad58' if nodes[n]['kind']=='Gap' else '#a8bde0') for n in ids]),
            text=display,textposition='middle right',
            textfont=dict(size=10,color='#e7f0fa'),hovertext=hover,
            hovertemplate='%{hovertext}<extra></extra>',showlegend=False))
    for i,label in enumerate(ROUTE):
        fig.add_annotation(x=i,y=1.065,showarrow=False,
                           text=f'<b>{label.upper()}</b>',
                           font=dict(color='#e7f0fa',size=12))
    fig.update_layout(height=height,paper_bgcolor='#101b2b',plot_bgcolor='#101b2b',
        margin=dict(l=55,r=125,t=65,b=30),showlegend=False,dragmode='pan',
        xaxis=dict(visible=False,range=[-.3,5.55]),
        yaxis=dict(visible=False,range=[-.07,1.12]))
    return fig


def render_capital_network():
    st.title('Global Capital Intelligence Network')
    st.caption('GLOBAL → ROTATION → COUNTRY → SECTOR → COMPANY → FACTOR · verified memberships')
    period = st.radio('Lookback',('1m','3m','6m'),index=1,
                      horizontal=True,key='network_period_v3')
    table, diagnostics = build_model(period,CACHE)
    breadth = global_breadth_score(table)
    score = 'N/A' if breadth['score'] is None else f"{breadth['score']:.1f} / 100"
    a,b,c = st.columns(3)
    a.metric('Global rotation breadth',score)
    b.metric('Countries classified',f"{breadth['classified']} / {breadth['tracked']}")
    c.metric('Verified companies',str(table.loc[table.company_id.ne(''),'company_id'].nunique()))
    st.caption('Global score is equal-weighted **country rotation breadth** (Leading=100, '
               'Improving=66.7, Weakening=33.3, Lagging=0). It is **not** an ACWI '
               'return, global capital-flow measurement, or market-cap-weighted score. '
               'Unclassified countries are excluded.')
    if diagnostics['classified_countries'] < diagnostics['tracked_countries']:
        st.warning('Some country ETF rotations are unavailable. Missing data stays Unclassified.')
    view=st.radio('View',('Overview','Sector / Factor','Individual Companies'),
                  horizontal=True,key='network_view_v3')
    def pick(col,idcol=None):
        if idcol is None:
            return sorted(x for x in table[col].unique() if x)
        entries=table[[col,idcol,'scope']].drop_duplicates()
        return {f'{r[col]} [{r["scope"]}]':r[idcol]
                for r in entries.to_dict('records') if r[col] and r[idcol]}
    sopts=pick('Sector','sector_id')
    fopts=pick('Factor','factor_id')
    copts=pick('Company','company_id')
    with st.expander('Filters · multi-select · unrelated paths disappear',
                     expanded=view!='Overview'):
        a,b,c=st.columns(3)
        with a:
            q=st.multiselect('Rotations',pick('Rotation'),key='network_filter_q_v3')
            countries=st.multiselect('Countries / Global direct',pick('Country'),
                                     key='network_filter_country_v3')
        with b:
            sectors=st.multiselect('Sectors',list(sopts),key='network_filter_s_v3')
            factors=st.multiselect('Factors',list(fopts),key='network_filter_f_v3')
        with c:
            companies=st.multiselect('Individual companies',list(copts),
                                     key='network_filter_c_v3')
            matching=st.radio('Match selected sectors / factors',('Any','All'),
                              horizontal=True,key='network_match_v3')
    filtered=filter_model(table,q,countries,[sopts[s] for s in sectors],
                          [copts[x] for x in companies],
                          [fopts[x] for x in factors],matching=matching)
    if filtered.empty:
        st.info('No verified paths match the selected filters.')
        return
    unique_companies=sorted(filtered.loc[filtered.company_id.ne(''),'company_id'].unique())
    show_all=st.checkbox('Show all matching companies (may be slow)',
                         value=False,key='network_show_all_v3')
    max_companies=None if show_all else (45 if view=='Overview' else 100)
    rendered=filtered
    if max_companies is not None and len(unique_companies)>max_companies:
        keep=set(unique_companies[:max_companies])
        rendered=filtered[(filtered.company_id.isin(keep)) |
            ((filtered.company_id=='') & (filtered.evidence.isin(
                ('country-rotation-only','global-scope'))))]
    nodes,edges=to_graph(rendered)
    warnings=validate_model(rendered,nodes,edges)
    if warnings:
        st.error('Graph validation failed: '+'; '.join(warnings))
        return
    st.caption(f'{len(nodes):,} nodes · {len(edges):,} adjacent links · '
               f'{len(unique_companies):,} matching companies '
               f'({min(len(unique_companies),max_companies) if max_companies else len(unique_companies)} displayed)')
    st.plotly_chart(plot_model(nodes,edges),use_container_width=True,
                    config={'scrollZoom':True,'displaylogo':False})
    st.caption('Dashed amber paths indicate a **missing sector relationship**, not '
               'a verified holding. Factor-only observations have a visible evidence gap. '
               'Unmapped factors with no company are kept in the table, not falsely linked.')
    with st.expander('Backend relationship table and data coverage'):
        st.dataframe(filtered[list(ROUTE)+['evidence','sector_rotation',
                         'factor_rotation','as_of']],hide_index=True,
                     use_container_width=True)
        st.download_button('Download complete six-column model CSV',
            table.to_csv(index=False).encode('utf-8'),
            file_name=f'capital_network_model_{period}.csv',mime='text/csv')
        st.json(diagnostics)
