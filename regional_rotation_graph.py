"""Region-specific, market-relative leading / lagging knowledge graph.

No network calls or heavy scoring on page load. Shows independently verified
sector and factor connections rather than arbitrary high-membership companies.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT=Path(__file__).resolve().parent
STORE=ROOT/'data'/'dashboard_cache'/'rotation_graphs'
BG='#0B1220'; PANEL='#142137'; TEXT='#E7EEF9'
COLORS={'Leading':'#4BD6A4','Lagging':'#F18A9A','Sector':'#51B7E8','Factor':'#F6BA64'}

@st.cache_data(show_spinner=False, max_entries=36)
def _read(path,mtime):
    if not Path(path).is_file():return pd.DataFrame()
    try:return pd.read_csv(path,keep_default_na=False)
    except (OSError,ValueError,pd.errors.EmptyDataError):return pd.DataFrame()

def _load(region,window,kind):
    p=STORE/f'{region.lower()}_{window}_{kind}.csv'
    return _read(str(p),p.stat().st_mtime_ns if p.exists() else 0)

def _manifest():
    p=STORE/'manifest.json'
    try:return json.loads(p.read_text())
    except (OSError,ValueError):return {}

def _sources(value):
    if pd.isna(value):return []
    return [p.strip() for p in str(value).split(' · ') if p.strip()]

def _draw(df,side,n):
    selection=df[df.Category.eq(side)].sort_values(['Rank','Score'],ascending=[True,False]).head(n)
    if selection.empty:
        st.info(f'No {side.lower()} companies with verified **both-sector-and-factor** evidence for this period.')
        return
    rows=selection.to_dict('records')
    sectors=sorted({s for r in rows for s in _sources(r.get('Sector sources',''))})
    factors=sorted({s for r in rows for s in _sources(r.get('Factor sources',''))})
    nodes=[]
    for side_name,x,labels in [('Sector',-2.3,sectors),('Factor',2.3,factors)]:
        for j,label in enumerate(labels):
            y= (len(labels)-1)*0.5-j
            nodes.append((side_name,label,x,y))
    positions={(kind,label):(x,y) for kind,label,x,y in nodes}
    span=max(len(rows),len(sectors),len(factors),4)
    loc={str(row['company_key']):(0.0,(len(rows)-1)*0.5-i) for i,row in enumerate(rows)}
    ex=[];ey=[]
    for row in rows:
        dest=loc[str(row['company_key'])]
        for kind,column in [('Sector','Sector sources'),('Factor','Factor sources')]:
            for label in _sources(row.get(column,'')):
                pos=positions.get((kind,label))
                if pos:
                    ex.extend([pos[0],dest[0],None]);ey.extend([pos[1],dest[1],None])
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=ex,y=ey,mode='lines',line=dict(color='rgba(133,164,200,.27)',width=1),hoverinfo='skip',showlegend=False))
    for kind in ('Sector','Factor'):
        group=[v for v in nodes if v[0]==kind]
        if group:
            fig.add_trace(go.Scatter(x=[v[2] for v in group],y=[v[3] for v in group],mode='markers+text',
                marker=dict(size=17,color=COLORS[kind],line=dict(width=1,color=BG)),
                text=[v[1][:24]+'…' if len(v[1])>25 else v[1] for v in group],
                textposition='middle left' if kind=='Sector' else 'middle right',
                textfont=dict(size=10,color=TEXT),customdata=[v[1] for v in group],
                hovertemplate='%{customdata}<extra>'+kind+'</extra>',name=kind))
    fig.add_trace(go.Scatter(x=[loc[str(r['company_key'])][0] for r in rows],
        y=[loc[str(r['company_key'])][1] for r in rows],mode='markers+text',
        marker=dict(size=[max(14,min(28,12+math.sqrt(max(0,float(r['Score'])))*2)) for r in rows],
                    color=COLORS[side],line=dict(width=1,color=BG)),
        text=[f"#{int(r['Rank'])} {r['Ticker']}" for r in rows],textposition='middle center',
        textfont=dict(size=10,color=BG),name=f'{side} companies',
        customdata=[[r['Company'],r['Score'],r.get('Signal basis',''),r.get('Avg ETF % weight','N/A')] for r in rows],
        hovertemplate='<b>%{customdata[0]}</b><br>Signal strength: %{customdata[1]}<br>Basis: %{customdata[2]}<br>Avg ETF weight: %{customdata[3]}<extra></extra>'))
    fig.update_layout(height=max(510,min(1050,span*46+160)),paper_bgcolor=PANEL,plot_bgcolor=PANEL,
        font=dict(color=TEXT),margin=dict(l=20,r=20,t=30,b=20),
        xaxis=dict(visible=False,range=[-4.3,4.3]),yaxis=dict(visible=False,range=[-span*.5-1,span*.5+1]),
        dragmode='pan',hovermode='closest',showlegend=False)
    st.plotly_chart(fig,use_container_width=True,config={'scrollZoom':True,'displaylogo':False})

def render_graph(region):
    st.markdown(f'## {"🌍" if region=="Global" else "🇺🇸" if region=="USA" else "🇮🇳"} {region} Market Knowledge Graph')
    st.caption('Sector & factor market rotation → constituent evidence → leading / lagging companies')
    left,right=st.columns([1,1])
    period=left.selectbox('Signal period',['1m','3m','6m'],index=1,format_func=lambda x:{'1m':'1 month','3m':'3 months','6m':'6 months'}[x],key=f'kg_period_{region}')
    limit=right.selectbox('Companies in graph',[10,15,20,30],index=1,key=f'kg_count_{region}')
    companies=_load(region,period,'companies');signals=_load(region,period,'signals')
    status=_manifest().get('regions',{}).get(f'{region.lower()}_{period}',{})
    if companies.empty and signals.empty:
        st.warning('No market-rotation snapshot is available. Run **Build Regional Market Knowledge Graphs** after the holdings and market-price refresh workflows.')
        if status.get('error'):st.error('Snapshot builder: '+str(status['error']))
        st.caption(f"Saved holdings: {status.get('holdings_records','N/A')} · rotation series: {status.get('rotation_signals','N/A')}")
        return
    leading=companies[companies.Category.eq('Leading')] if 'Category' in companies else pd.DataFrame()
    lagging=companies[companies.Category.eq('Lagging')] if 'Category' in companies else pd.DataFrame()
    c=st.columns(4)
    c[0].metric('Leading companies',len(leading));c[1].metric('Lagging companies',len(lagging))
    c[2].metric('Verified rotation signals',len(signals));c[3].metric('Unmapped ETF sources',status.get('unmapped_sources','N/A'))
    if status.get('signal_asof'):st.caption('Market data as of '+str(status['signal_asof']))
    views=st.tabs(['Leading companies','Lagging companies','Market rotation','Data coverage'])
    for tab,side in [(views[0],'Leading'),(views[1],'Lagging')]:
        with tab:
            _draw(companies,side,limit) if not companies.empty else st.info('No companies qualify for this classification.')
            subset=leading if side=='Leading' else lagging
            if not subset.empty:
                cols=[v for v in ['Rank','Ticker','Company','Score','Sector indices','Factor indices','Avg ETF % weight','Sector sources','Factor sources','Signal basis'] if v in subset]
                st.dataframe(subset[cols],hide_index=True,use_container_width=True,height=360)
    with views[2]:
        if signals.empty:st.info('No source price histories passed coverage checks.')
        else:
            cols=[k for k in ['kind','label','quadrant','relative_strength','rs_momentum','as_of'] if k in signals]
            st.dataframe(signals[cols],hide_index=True,use_container_width=True,height=420)
    with views[3]:
        st.json(status)
        if status.get('error'):st.error(status['error'])
        st.caption('Leading/lagging describes **benchmark-relative sector and factor positioning**, not verified individual stock-price momentum or investment value. A company must appear in qualifying sector AND factor sources. Missing evidence is not a lagging signal.')
