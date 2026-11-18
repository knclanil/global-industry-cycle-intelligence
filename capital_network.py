"""Interactive, evidence-labeled market relationship network (not fund-flow data)."""
from datetime import date, timedelta
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard import prices_cached
from factor_holdings import parse_holdings, score_holdings, FACTORS
import country_market_data, global_asset_market_data, usa_asset_market_data, india_asset_market_data
import global_market_data, market_data, india_market_data
import global_factor_market_data, usa_factor_market_data, india_factor_market_data

SOURCES = {
 'Countries':country_market_data,'Global Assets':global_asset_market_data,
 'USA Assets':usa_asset_market_data,'India Assets':india_asset_market_data,
 'Global Sectors':global_market_data,'USA Sectors':market_data,'India Sectors':india_market_data,
 'Global Factors':global_factor_market_data,'USA Factors':usa_factor_market_data,'India Factors':india_factor_market_data,
}
CACHE_KEYS={'Countries':'Countries','Global Assets':'GlobalAssets','USA Assets':'USAAssets','India Assets':'IndiaAssets','Global Sectors':'Global','USA Sectors':'USA','India Sectors':'India','Global Factors':'GlobalFactors','USA Factors':'USAFactors','India Factors':'IndiaFactors'}
COLORS={'Leading':'#27c999','Improving':'#5c9fff','Weakening':'#e9ad58','Lagging':'#ef6b83','Unavailable':'#73849b'}

def score_rows(rows):
    """Peer-relative 0..100 percentile scores, not investment flows."""
    d=rows.copy()
    if d.empty:return d
    for col,out in [('Relative strength (%)','rs_percentile'),('RS momentum (pp)','momentum_percentile')]:
        d[out]=d[col].rank(pct=True,method='average')*100
    d['Network Score']=(.6*d.rs_percentile+.4*d.momentum_percentile).round(1)
    return d

def fetch_layer(layer,start,end,lookback):
    module=SOURCES[layer]
    frames=prices_cached(CACHE_KEYS[layer],start-timedelta(days=600),end)
    report=module.validate(frames,end)
    if report['status']=='FAIL':raise ValueError('; '.join(report['errors'][:3]))
    rows,*_=module.calculate(frames,list(module.SECTORS),start,end,lookback)
    if rows.empty:raise ValueError('No validated observations for selected window')
    return score_rows(rows),report

def node(node_id,label,kind,layer=None,record=None):
    data={'id':node_id,'label':str(label),'kind':kind,'layer':layer,'score':None,'quadrant':None,'ticker':None,'return':None,'relative':None}
    if record is not None:
        data.update(score=float(record['Network Score']),quadrant=str(record['Quadrant']),ticker=str(record['ETF']),relative=float(record['Relative strength (%)']),**{'return':float(record['Return (%)'])})
    return data

def build_graph(path,market,layers,top_n,holdings=None):
    """Only create edges supported by price series or uploaded constituent files."""
    nodes={'root':node('root','GLOBAL','root')}; edges=[]
    def add(n,parent):
        nodes[n['id']]=n
        if parent in nodes:edges.append((parent,n['id']))
    if path=='Country → assets → sectors → companies':
        countries=layers.get('Countries',pd.DataFrame())
        for _,r in pd.concat([countries[countries['ETF'].isin(['SPY','INDA'])], countries.nlargest(top_n,'Network Score')]).drop_duplicates('ETF').iterrows():
            cid='country:'+str(r['ETF']);add(node(cid,r['Sector'],'country','Countries',r),'root')
        # Country-specific asset data is available only for USA and India.
        for market_name,match,asset_layer,sector_layer in [('USA',('United States','USA','US'),'USA Assets','USA Sectors'),('India',('India',),'India Assets','India Sectors')]:
            country_ids=[n['id'] for n in nodes.values() if n['kind']=='country' and (any(s.lower() in n['label'].lower() for s in match) or (market_name=='USA' and n['ticker'] in ('EUSA','SPY','IVV')))]
            if not country_ids:continue
            cid=country_ids[0]
            for _,r in pd.concat([layers.get(asset_layer,pd.DataFrame())[layers.get(asset_layer,pd.DataFrame())['Sector'].str.contains('Equit|Nifty',case=False,na=False)], layers.get(asset_layer,pd.DataFrame()).nlargest(top_n,'Network Score')]).drop_duplicates('ETF').iterrows() if not layers.get(asset_layer,pd.DataFrame()).empty else []:
                aid=f'{market_name}:asset:{r["ETF"]}';add(node(aid,r['Sector'],'asset',asset_layer,r),cid)
                if any(t in str(r['Sector']).lower() for t in ('equity','stock','nifty 50','s&p 500')):
                    for _,s in layers.get(sector_layer,pd.DataFrame()).nlargest(top_n,'Network Score').iterrows():
                        sid=f'{market_name}:sector:{s["ETF"]}';add(node(sid,s['Sector'],'sector',sector_layer,s),aid)
        # No sector-company edges without verified sector constituents.
    else:
        assets=layers.get('Global Assets',pd.DataFrame())
        for _,r in pd.concat([assets[assets['ETF']=='VT'], assets.nlargest(top_n,'Network Score')]).drop_duplicates('ETF').iterrows():
            aid='global:asset:'+str(r['ETF']);add(node(aid,r['Sector'],'asset','Global Assets',r),'root')
            if any(t in str(r['Sector']).lower() for t in ('equity','stock')):
                factor_layer=market+' Factors'
                for _,f in layers.get(factor_layer,pd.DataFrame()).nlargest(top_n,'Network Score').iterrows():
                    fid='factor:'+market+':'+str(f['ETF']);add(node(fid,f['Sector'],'factor',factor_layer,f),aid)
                    if holdings is not None and not holdings.empty:
                        subset=holdings[holdings['factor'].astype(str).str.upper()==str(f['ETF']).upper()].nlargest(top_n,'weight')
                        for _,h in subset.iterrows():
                            identity=str(h.get('isin','')).strip() or str(h.get('ticker','')).strip() or str(h['company']).strip()
                            hid='company:'+market+':'+identity.upper()
                            if hid not in nodes:nodes[hid]=node(hid,h['company'],'company')
                            edges.append((fid,hid))
    return nodes,edges

def layout(nodes,edges):
    """Deterministic left-to-right hierarchy with shared company nodes."""
    levels={'root':0,'country':1,'asset':2,'sector':3,'factor':3,'company':4}
    if any(n['kind']=='country' for n in nodes.values()):levels['asset']=2
    grouped={}
    for n in nodes.values():grouped.setdefault(levels[n['kind']],[]).append(n)
    pos={}
    for depth,items in grouped.items():
        items.sort(key=lambda n:(-float(n['score'] or 0),n['label']))
        for i,n in enumerate(items):pos[n['id']]=(depth*2.8,(len(items)-1)*.68-i*1.36)
    return pos

def make_figure(nodes,edges,selected=None):
    pos=layout(nodes,edges);fig=go.Figure()
    for a,b in edges:
        if a not in pos or b not in pos:continue
        x1,y1=pos[a];x2,y2=pos[b]
        fig.add_trace(go.Scatter(x=[x1,x2],y=[y1,y2],mode='lines',line=dict(color='#4a617f' if selected not in (a,b) else '#c4d5ee',width=1.1 if selected not in (a,b) else 3),hoverinfo='skip',showlegend=False))
    for kind in ('root','country','asset','sector','factor','company'):
        items=[n for n in nodes.values() if n['kind']==kind]
        if not items:continue
        fig.add_trace(go.Scatter(x=[pos[n['id']][0] for n in items],y=[pos[n['id']][1] for n in items],mode='markers+text',
          text=[(n['label'][:19]+'…' if len(n['label'])>20 else n['label']) for n in items],textposition='top center',
          textfont=dict(size=10,color='#e3ebf7'),marker=dict(size=[27 if n['id']==selected else 17+min((n['score'] or 50)/11,9) for n in items],color=[COLORS.get(n['quadrant'],'#a1b3ce') for n in items],line=dict(color='#e5f0ff',width=1)),
          customdata=[[n['id']] for n in items],hovertemplate='%{text}<extra>'+kind.title()+'</extra>',name=kind.title(),showlegend=False))
    fig.update_layout(template='plotly_dark',paper_bgcolor='#0b1220',plot_bgcolor='#0b1220',height=690,margin=dict(l=30,r=30,t=45,b=25),dragmode='pan',clickmode='event+select',xaxis=dict(visible=False,range=[-.8,max((p[0] for p in pos.values()),default=1)+1]),yaxis=dict(visible=False),uirevision='network')
    return fig

def render_capital_network():
    st.title('🌐 Global Capital Intelligence Network')
    st.caption('Interactive market leadership relationships • **Not measured capital flows** • Company edges require uploaded, verifiable holdings')
    c1,c2,c3,c4=st.columns([2.4,1.4,1.5,2.7])
    with c1:path=st.selectbox('EXPLORATION PATH',['Country → assets → sectors → companies','Assets → equity → factors → companies'])
    with c2:market=st.selectbox('FACTOR MARKET',['Global','USA','India'],disabled=path.startswith('Country'))
    with c3:lookback=st.select_slider('RELATIVE TIME',options=list(country_market_data.LOOKBACKS),value='3M')
    with c4:period=st.date_input('FROM DATE → TO DATE',value=(date.today()-timedelta(days=365),date.today()),max_value=date.today())
    c5,c6,c7=st.columns([1.1,1.1,3])
    with c5:top_n=st.selectbox('TOP N PER BRANCH',[5,10,20],index=0)
    with c6:depth=st.slider('VISIBLE DEPTH',1,4,4)
    with c7:st.caption('Click a node for its verified score and relationships. Pan and zoom using the chart toolbar. Gray nodes have no comparable score.')
    if len(period)!=2 or period[0]>=period[1]:st.info('Choose a valid start and end date.');return
    start,end=period
    holdings=None
    if path.startswith('Assets'):
        with st.expander('Company constituents (optional; required to display company nodes)'):
            st.caption('Upload CSV/XLSX with factor, company, weight (%), and ideally ISIN, ticker, as_of, source. Factor identifiers must match the factor ETF/index ticker. Files are processed only in this session.')
            uploaded=st.file_uploader('Factor holdings files',type=['csv','xlsx'],accept_multiple_files=True,key='network_holdings')
            if uploaded:
                pieces=[]
                for file in uploaded:
                    try:pieces.append(parse_holdings(file,source=file.name))
                    except Exception as exc:st.warning(f'{file.name}: {exc}')
                if pieces:
                    holdings=pd.concat(pieces,ignore_index=True)
                    st.success(f'{len(holdings):,} positive-weight holdings loaded. As-of dates and completeness must be checked against issuer files.')
    requested=['Countries','USA Assets','India Assets','USA Sectors','India Sectors'] if path.startswith('Country') else ['Global Assets',market+' Factors']
    layers={};reports={};errors={}
    with st.spinner('Loading verified market prices and building network…'):
        for layer in requested:
            try:layers[layer],reports[layer]=fetch_layer(layer,start,end,lookback)
            except Exception as exc:errors[layer]=str(exc)
    if errors:
        with st.expander(f'Unavailable data layers ({len(errors)})',expanded=True):
            for k,v in errors.items():st.warning(f'{k}: {v}')
    if not layers:
        st.error('No market layers could be loaded. Network scores and connections have been withheld.');return
    nodes,edges=build_graph(path,market,layers,top_n,holdings)
    if depth<4:
        level={'root':0,'country':1,'asset':1 if path.startswith('Assets') else 2,'sector':3,'factor':2,'company':3}
        keep={nid for nid,n in nodes.items() if level[n['kind']]<=depth}
        nodes={k:v for k,v in nodes.items() if k in keep};edges=[(a,b) for a,b in edges if a in keep and b in keep]
    if not edges:st.info('No supported relationships for the current selection. Try a wider date range or another path.')
    selected=st.session_state.get('capital_selected')
    if selected not in nodes:selected=None
    event=st.plotly_chart(make_figure(nodes,edges,selected),use_container_width=True,key='capital_network_plot',on_select='rerun',selection_mode='points',config={'displaylogo':False,'scrollZoom':True})
    try:
        for point in event.selection.points:
            if point.get('customdata'):
                selected=point['customdata'][0];break
    except (AttributeError,KeyError,TypeError):pass
    if selected in nodes:st.session_state.capital_selected=selected
    if selected in nodes:
        n=nodes[selected]
        st.subheader('Selected node · '+n['label'])
        a,b,c,d=st.columns(4)
        a.metric('Type',n['kind'].title());b.metric('Rotation score',f"{n['score']:.1f}/100" if n['score'] is not None else 'N/A')
        c.metric('Regime',n['quadrant'] or 'Not scored');d.metric('Period return',f"{n['return']:+.2f}%" if n['return'] is not None else 'N/A')
        neighbors=[nodes[t] for x,y in edges for t in ([y] if x==selected else [x] if y==selected else []) if t in nodes]
        if neighbors:st.dataframe(pd.DataFrame([{'Connected node':x['label'],'Type':x['kind'],'Rotation score':x['score']} for x in neighbors]),hide_index=True,use_container_width=True)
        if n['layer']:st.caption(f"Source layer: {n['layer']} • Symbol: {n['ticker']} • Relative strength: {n['relative']:+.2f}% • Peer-normalized score is not comparable across unrelated universes.")
    st.caption(f"Showing {len(nodes)} nodes and {len(edges)} verified/proxy relationships. Scores: 60% peer RS percentile + 40% peer momentum percentile. Node color: green Leading, blue Improving, amber Weakening, red Lagging. Data layer validation: "+', '.join(f'{k} {v["status"]}' for k,v in reports.items()))
    if path.startswith('Country'):st.info('Country-specific asset and sector drill-down is currently supported for USA and India only. Sector → company edges are withheld until sector constituent files are available. Other country nodes remain at country level.')
    else:st.info('Factor → company connections appear only for uploaded holdings matching factor symbols. Their presence denotes constituent membership, not actual fund subscriptions/redemptions. Company consensus scoring remains available on Factor Holdings Comparison.')
