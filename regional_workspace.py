"""Unified read-only Global/USA/India views backed by Git materialized snapshots."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'data' / 'dashboard_cache'
THEME = {'background':'#0B1220','panel':'#142137','line':'#2A3C55','text':'#E7EEF9',
         'sector':'#51B7E8','factor':'#F6BA64','company':'#92E0B9'}

def _mtime(path:Path):return path.stat().st_mtime_ns if path.exists() else 0

@st.cache_data(show_spinner=False,max_entries=45)
def _csv(path:str,stamp:int):
    if not Path(path).exists():return pd.DataFrame()
    return pd.read_csv(path,keep_default_na=False)


def load(region,table):
    path=CACHE/f'{region.lower()}_{table}.csv'
    return _csv(str(path),_mtime(path))

def _header(region,subtitle):
    st.markdown(f'## {"🌍" if region=="Global" else "🇺🇸" if region=="USA" else "🇮🇳"} {region} Intelligence')
    st.caption(subtitle)

def _summary(region):
    company=load(region,'companies'); indices=load(region,'indices')
    a,b,c,d=st.columns(4)
    a.metric('Verified companies',f'{len(company):,}')
    b.metric('Source indices / ETFs',f'{len(indices):,}')
    c.metric('Constituent memberships',f'{pd.to_numeric(company.get("index_memberships",pd.Series(dtype=float)),errors="coerce").sum():,.0f}')
    d.metric('Financial statement coverage',f'{int(company.financial_status.eq("Available").sum()):,}' if 'financial_status' in company else 'N/A')
    return company,indices

def _source_table(indices):
    if indices.empty:return st.info('No index snapshots collected. Run the relevant scheduled data refresh and cache build.')
    filt=st.text_input('Find a sector, factor or ETF',key='ws_indices_filter')
    if filt:indices=indices[indices.index_name.astype(str).str.contains(filt,case=False,regex=False)]
    cols=[x for x in ['index_name','category','factor_family','constituents','snapshot_utc'] if x in indices]
    st.dataframe(indices[cols].rename(columns={'index_name':'Index / ETF','category':'Type','factor_family':'Factor','constituents':'Companies','snapshot_utc':'As of'}),hide_index=True,use_container_width=True,height=420)

def _company_table(region,company,view='holdings'):
    if company.empty:return st.info('No verified constituent data in the materialized cache yet.')
    query=st.text_input('Search company or ticker',key=f'ws_company_{region}_{view}',placeholder='Name or symbol')
    df=company.copy()
    if query:
        df=df[df.symbol.astype(str).str.contains(query,case=False,regex=False) | df.company_name.astype(str).str.contains(query,case=False,regex=False)]
    cols=[x for x in ['symbol','company_name','country','industry','index_memberships','avg_etf_weight_pct','sector_indices','factor_families','factor_indices'] if x in df]
    st.dataframe(df[cols].rename(columns={'symbol':'Ticker','company_name':'Company','industry':'Sector / industry',
        'country':'Country', 'index_memberships':'Index memberships','avg_etf_weight_pct':'Avg ETF wt (%)',
        'sector_indices':'Sector sources','factor_indices':'Factor sources','factor_families':'Factor families'}),hide_index=True,use_container_width=True,height=460)
    st.download_button('Export filtered companies',df.to_csv(index=False),file_name=f'{region.lower()}_companies.csv',mime='text/csv',key=f'ws_export_{region}_{view}')

def _financials(region,company):
    if company.empty:return st.info('Financial coverage will appear after the scheduled company-data build.')
    fields={'revenue':'Revenue','net_income':'Net income','roe':'ROE','operating_margin':'Operating margin','net_margin':'Net margin','pe':'P/E'}
    avail=[k for k in fields if k in company]
    if not avail:
        st.info('Company financial snapshots have not been materialized for this market. Financials are not inferred from ETF membership.')
        return
    df=company[['symbol','company_name','industry']+avail].copy()
    for col in avail:df[col]=pd.to_numeric(df[col],errors='coerce')
    score=df[avail].notna().sum(axis=1)
    valid=df.loc[score.gt(0)].copy()
    st.metric('Companies with any of these financial observations',f'{len(valid):,} / {len(df):,}')
    if valid.empty:
        st.info('No usable financial numbers yet. The collected quote snapshot may not contain annual statement values.')
    else:
        shown=valid.rename(columns={'symbol':'Ticker','company_name':'Company','industry':'Industry',**fields})
        st.dataframe(shown,hide_index=True,use_container_width=True,height=410)
        st.caption('Reported / derived financial figures · Check each source period and currency before comparing companies.')

def _index_financial_summary(region):
    frame=load(region,'index_financial_summary')
    if frame.empty:
        st.info('Index-level financial summary awaits verified company financial statements.')
        return
    usable=frame.copy()
    cols=['index_name','category','constituents','financial_records','median_revenue',
          'median_net_income','median_roe','median_operating_margin','median_net_margin','median_pe']
    keep=[x for x in cols if x in usable]
    shown=usable[keep].rename(columns={'index_name':'Sector / factor ETF','category':'Type',
          'constituents':'Constituents','financial_records':'Revenue observations',
          'median_revenue':'Median revenue','median_net_income':'Median income',
          'median_roe':'Median ROE','median_operating_margin':'Median operating margin',
          'median_net_margin':'Median net margin','median_pe':'Median P/E'})
    st.dataframe(shown,hide_index=True,use_container_width=True,height=420)
    st.caption('Unweighted medians of observed constituent fundamentals. Incomplete source coverage is shown explicitly.')

def _matrix(region):
    frame=load(region,'sector_factor_matrix')
    if frame.empty:return st.info('No verified sector–factor intersections in the saved dataset.')
    if not {'sector_index','factor_family','companies'}.issubset(frame):return st.info('Sector–factor snapshot schema needs rebuilding.')
    grid=frame.pivot_table(index='sector_index',columns='factor_family',values='companies',aggfunc='sum',fill_value=0)
    if grid.empty:return
    graph=go.Figure(go.Heatmap(z=grid.to_numpy(),x=list(grid.columns),y=list(grid.index),
                             colorscale=[[0,'#15243A'],[0.4,'#245F82'],[1,'#52CBEA']],
                             hovertemplate='%{y} × %{x}: %{z} securities<extra></extra>'))
    graph.update_layout(paper_bgcolor=THEME['background'],plot_bgcolor=THEME['background'],font_color=THEME['text'],
                        margin=dict(l=10,r=10,t=15,b=10),height=max(380,32*len(grid)),xaxis_side='top')
    st.plotly_chart(graph,use_container_width=True)
    with st.expander('Detailed intersection counts'):
        st.dataframe(grid,use_container_width=True)

def render_analysis(region):
    _header(region,'Sector → Factor → Constituents → Verified financial data · Saved Git snapshots')
    company,indices=_summary(region)
    if region == 'Global' and not company.empty and 'country' in company:
        countries=sorted({str(x).strip() for x in company['country'].dropna() if str(x).strip()})
        if countries:
            selected=st.selectbox('Company domicile', ['All countries']+countries, key='global_country_filter',
                                  help='Filters company-level views by the source holdings country. Index totals remain global.')
            if selected!='All countries':
                company=company[company['country'].astype(str).str.strip().eq(selected)].copy()
    overview, members, sources, overlap, finance = st.tabs(['Overview','Company holdings','All source indices','Sector × Factor','Financial coverage'])
    with overview:
        st.markdown('#### Sector and factor coverage')
        if not indices.empty:
            counts=indices.groupby('category',dropna=False).agg(Indices=('index_name','nunique'),Companies=('constituents','sum')).reset_index()
            st.bar_chart(counts.set_index('category')[['Indices']],horizontal=True,color=THEME['sector'])
            st.caption('Sum of index constituent counts may include companies present in multiple indices.')
        _company_table(region,company.head(60).copy(),view='overview')
    with members:_company_table(region,company,view='holdings')
    with sources:_source_table(indices)
    with overlap:_matrix(region)
    with finance:
        _index_financial_summary(region)
        _financials(region,company)
    with st.expander('Data refresh and methodology'):
        path=CACHE/'manifest.json'
        if path.exists():
            try:
                meta=json.loads(path.read_text());st.caption(f"Cache built: {meta.get('built_utc','Unknown')}")
            except (OSError,ValueError):pass
        st.caption('Market prices refresh daily when providers succeed. ETF and NSE holdings update when source constituents change; company financial reports update on their own schedules. No failed request deletes verified history.')

def _link_rows(region,company,indices):
    """Create a bounded 2D graph from actual saved source relationships."""
    if company.empty or indices.empty:return [],[],[]
    available=set(indices.index_name.astype(str))
    chosen=company.sort_values('index_memberships',ascending=False).head(38)
    edges=[];names=set()
    for row in chosen.itertuples(index=False):
        person=str(row.symbol)
        for text in [row.sector_indices,row.factor_indices]:
            for src in (str(text).split(' | ') if pd.notna(text) else []):
                if src and src in available:
                    edges.append((person,src));names.add(src)
    return chosen.to_dict('records'),sorted(names),edges

def render_graph(region):
    _header(region,'2D holdings network · Sector and factor source connections')
    company,indices=_summary(region)
    companies,sources,edges=_link_rows(region,company,indices)
    if not edges:
        st.info('No verified index–company connections to render. Run the holdings refresh and build the dashboard cache.')
        return
    import math
    # Fixed deterministic polar positions: no force simulation, no 3D, and stable node order.
    sectors=set(indices.loc[indices.category.astype(str).str.contains('Sector|Thematic',case=False,regex=True),'index_name'])
    positions={}
    for n,name in enumerate(sources):
        angle=2*math.pi*n/max(1,len(sources));positions[name]=(1.0*math.cos(angle),1.0*math.sin(angle))
    for n,row in enumerate(companies):
        angle=2*math.pi*n/max(1,len(companies));positions[str(row['symbol'])]=(.47*math.cos(angle),.47*math.sin(angle))
    ex,ey=[],[]
    for a,b in edges:
        x1,y1=positions[a];x2,y2=positions[b];ex += [x1,x2,None];ey += [y1,y2,None]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=ex,y=ey,mode='lines',line=dict(color='#314967',width=0.7),hoverinfo='skip',showlegend=False))
    for kind,nodes,color,size in [('Sector', [s for s in sources if s in sectors],THEME['sector'],13),
                                  ('Factor', [s for s in sources if s not in sectors],THEME['factor'],12),
                                  ('Company',[str(r['symbol']) for r in companies],THEME['company'],8)]:
        if not nodes:continue
        fig.add_trace(go.Scatter(x=[positions[n][0] for n in nodes],y=[positions[n][1] for n in nodes],mode='markers+text',
            marker=dict(size=size,color=color,line=dict(color='#15253B',width=1)),text=[n if kind=='Company' else (n[:20]+'…' if len(n)>20 else n) for n in nodes],
            textposition='top center',textfont=dict(size=9,color=THEME['text']),name=kind,
            customdata=nodes,hovertemplate='%{customdata}<extra>'+kind+'</extra>'))
    if region == 'Global' and any('country' in row and str(row.get('country','')).strip() for row in companies):
        # Country links use only explicit holdings country assignments, never guesses from symbols.
        country_names=sorted({str(row.get('country','')).strip() for row in companies if str(row.get('country','')).strip()})
        for n,country in enumerate(country_names):
            angle=2*math.pi*n/max(1,len(country_names))
            positions['country:'+country]=(1.40*math.cos(angle),1.40*math.sin(angle))
        cx,cy=[],[]
        for row in companies:
            country=str(row.get('country','')).strip()
            ticker=str(row['symbol'])
            if country and ticker in positions:
                x1,y1=positions[ticker];x2,y2=positions['country:'+country]
                cx.extend([x1,x2,None]);cy.extend([y1,y2,None])
        fig.add_trace(go.Scatter(x=cx,y=cy,mode='lines',line=dict(color='#566a82',width=0.8,dash='dot'),hoverinfo='skip',showlegend=False))
        fig.add_trace(go.Scatter(x=[positions['country:'+c][0] for c in country_names],
                                 y=[positions['country:'+c][1] for c in country_names],mode='markers+text',
                                 marker=dict(size=16,color='#b79cf8',line=dict(color='#15253B',width=1)),
                                 text=country_names,textposition='top center',textfont=dict(size=10,color=THEME['text']),
                                 name='Country',hovertemplate='%{text}<extra>Country</extra>'))
    fig.update_layout(height=740,margin=dict(l=5,r=5,t=30,b=5),paper_bgcolor=THEME['background'],plot_bgcolor=THEME['background'],
        font_color=THEME['text'],xaxis=dict(visible=False,range=[-1.75,1.75],scaleanchor='y'),
        yaxis=dict(visible=False,range=[-1.75,1.75]),dragmode='pan')
    st.plotly_chart(fig,use_container_width=True)
    st.caption('Shows up to 38 high-membership companies. Global country links appear when verified country metadata is saved. This is a coverage graph, not a performance ranking.')
