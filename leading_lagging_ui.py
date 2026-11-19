"""Independent Global/USA/India leading & lagging constituent graph."""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from leading_lagging_engine import rotation_signals, load_holdings, build_lists

COLORS={'Leading':'#3fd3ac','Lagging':'#fb8295','sector':'#51b7e8','factor':'#a89aff'}

@st.cache_data(show_spinner=False, ttl=900)
def _load(region, lookback, holdings_timestamp, market_timestamp):
    holdings = load_holdings(region)
    signals = rotation_signals(region, lookback)
    return holdings, signals


def _graph(ranking:pd.DataFrame, side:str, count:int):
    leaders = ranking[ranking.Category==side].nsmallest(count,'Rank')
    if leaders.empty:
        st.info(f'No verified {side.lower()} companies with both sector and factor evidence.')
        return
    import math
    # Strictly 2D; sector/factor sources at left/right, companies centered.
    fig=go.Figure()
    companies=leaders.to_dict('records')
    source_counts={'sector':{},'factor':{}}
    for r in companies:
        for kind,col in (('sector','Sector sources'),('factor','Factor sources')):
            for src in str(r[col]).split(' · '):
                if src: source_counts[kind][src]=source_counts[kind].get(src,0)+1
    loc={}
    for kind,x in (('sector',-1.9),('factor',1.9)):
        for j,name in enumerate(sorted(source_counts[kind])):
            n=len(source_counts[kind]); y=(n-1)/2-j
            loc[(kind,name)]=(x,float(y)*max(0.43,min(1.5,8/max(n,1))))
    height=max(460,min(950, len(companies)*55+200))
    comloc={r['company_key']:(0,float((len(companies)-1)/2-i)*min(0.9,8/max(len(companies),1))) for i,r in enumerate(companies)}
    # Render lines in one trace for responsiveness.
    xs=[];ys=[]
    for r in companies:
        x2,y2=comloc[r['company_key']]
        for kind,col in (('sector','Sector sources'),('factor','Factor sources')):
            for src in str(r[col]).split(' · '):
                if (kind,src) in loc:
                    x1,y1=loc[(kind,src)]
                    xs.extend((x1,x2,None));ys.extend((y1,y2,None))
    fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',line=dict(color='rgba(123,160,196,0.25)',width=1),
                             hoverinfo='skip',showlegend=False))
    for kind in ('sector','factor'):
        names=sorted(source_counts[kind]); coords=[loc[(kind,n)] for n in names]
        if coords:
            fig.add_trace(go.Scatter(x=[c[0] for c in coords],y=[c[1] for c in coords],mode='markers+text',
                text=[(n[:24]+'…') if len(n)>25 else n for n in names],
                textposition='middle left' if kind=='sector' else 'middle right',
                marker=dict(size=[min(24,11+source_counts[kind][n]*2) for n in names],
                            color=COLORS[kind],line=dict(color='#294560',width=1)),
                customdata=names, hovertemplate='%{customdata}<extra></extra>',showlegend=False))
    fig.add_trace(go.Scatter(x=[comloc[r['company_key']][0] for r in companies],
        y=[comloc[r['company_key']][1] for r in companies],mode='markers+text',
        marker=dict(size=[min(30,14+math.sqrt(r['Score'])*3) for r in companies],color=COLORS[side],
                    line=dict(color='#142137',width=2)),
        text=[f"#{r['Rank']} {r['Ticker']}" for r in companies],textposition='middle center',
        textfont=dict(color='#071726',size=10),
        customdata=[[r['Company'],r['Score'],r['Sector indices'],r['Factor indices']] for r in companies],
        hovertemplate='<b>%{customdata[0]}</b><br>Evidence score: %{customdata[1]:.2f}<br>Sector indices: %{customdata[2]}<br>Factor indices: %{customdata[3]}<extra></extra>',showlegend=False))
    fig.update_layout(paper_bgcolor='#142137',plot_bgcolor='#142137',font=dict(color='#dce8f8'),
                      xaxis=dict(visible=False,range=[-3.8,3.8],fixedrange=False),
                      yaxis=dict(visible=False,scaleanchor=None),hovermode='closest',
                      margin=dict(l=12,r=12,t=15,b=15),height=height,dragmode='pan')
    st.plotly_chart(fig,use_container_width=True,config={'scrollZoom':True,'displaylogo':False})


def _mtime(path):
    return path.stat().st_mtime_ns if path.exists() else 0


def render_leading_lagging_graph():
    from leading_lagging_engine import DATA
    st.markdown('## ◈ Leading & Lagging Companies')
    st.caption('Sector × factor rotation · Evidence-based company lists · Three independent markets')
    region=st.segmented_control('Market',['Global','USA','India'],default='Global',key='ll_region')
    if region is None: region='Global'
    c1,c2,c3=st.columns([1,1,1])
    lookback=c1.selectbox('Rotation lookback',['1 month','3 months','6 months'],index=1)
    L={'1 month':21,'3 months':63,'6 months':126}[lookback]
    max_companies=c2.selectbox('Graph companies',[10,15,20,30],index=1)
    show=c3.selectbox('View',['Graph & rankings','Rankings only'],index=0)
    from pathlib import Path
    h=DATA / ('india_holdings/constituents.csv' if region=='India' else 'holdings/latest_holdings.parquet')
    marketfiles=list((DATA/'market').rglob('*.parquet')) if (DATA/'market').exists() else []
    token=sum(p.stat().st_mtime_ns for p in marketfiles) if marketfiles else 0
    holdings,signals=_load(region,L,_mtime(h),token)
    if holdings.empty:
        st.warning('No verified holdings dataset found for this market. Run the existing holdings refresh workflow.')
        return
    if signals.empty:
        st.warning('No valid saved sector/factor rotation prices for this lookback. Run Nightly Market Refresh. No company is labeled lagging without market evidence.')
        return
    results, missing=build_lists(region,holdings,signals)
    leading=results[results.Category=='Leading'] if not results.empty else pd.DataFrame()
    lagging=results[results.Category=='Lagging'] if not results.empty else pd.DataFrame()
    s1,s2,s3,s4=st.columns(4)
    s1.metric('Leading companies',len(leading))
    s2.metric('Lagging companies',len(lagging))
    s3.metric('Verified rotation indices',len(signals))
    s4.metric('Unmapped sources',len(missing))
    if region != 'India':
        st.caption('USA/Global: where exact fund price mappings are unavailable, issuer fund titles are mapped to clearly labeled **sector/factor ETF category proxies**. Rankings reflect those proxies—not the source ETFs’ own returns or individual-company returns.')
    st.caption('Leading: positive relative strength and momentum on BOTH sides. Lagging: negative relative strength and momentum on BOTH sides. Improving/Weakening remain unclassified. These are index signals, not company-price performance or valuation.')
    if region != 'India' and len(missing):
        st.info('Some holdings funds have no unambiguous sector/factor proxy. See Rotation & coverage. Optional exact mappings: data/market/rotation_source_links.csv.')
    tabs=st.tabs(['▲ Leading','▼ Lagging','Rotation & coverage'])
    for tab,side,subset in [(tabs[0],'Leading',leading),(tabs[1],'Lagging',lagging)]:
        with tab:
            if subset.empty:
                st.info(f'No eligible {side.lower()} company has verified matching sector AND factor signals at this lookback.')
                continue
            if show=='Graph & rankings': _graph(results,side,max_companies)
            cols=['Rank','Ticker','Company','Score','Sector indices','Factor indices','Sector sources','Factor sources','Signal basis']
            if region!='India': cols.insert(6,'Exposure')
            st.dataframe(subset[cols].sort_values('Rank'),hide_index=True,use_container_width=True,
                column_config={'Score':st.column_config.NumberColumn('Evidence score',format='%.2f'),
                               'Exposure':st.column_config.NumberColumn('Sum ETF weight %',format='%.2f')})
            st.download_button(f'Download {side.lower()} CSV',subset.to_csv(index=False).encode(),file_name=f'{region.lower()}_{side.lower()}_companies.csv',mime='text/csv')
    with tabs[2]:
        st.caption('Source index signals, not individual-company stock returns. Only audited linkages are used.')
        st.dataframe(signals.rename(columns={'label':'Index / ETF','quadrant':'Rotation','as_of':'As of',
                          'relative_strength':'Relative strength %','rs_momentum':'Momentum pp'}),
                     hide_index=True,use_container_width=True)
        with st.expander(f'Unmapped source indices ({len(missing)})'):
            if not missing.empty: st.dataframe(missing,hide_index=True,use_container_width=True)
        st.caption('India missing full constituent weightage: each index membership counts once. USA/Global weights are reported ETF allocations. Index performance coverage and mapping depend on saved market data.')
