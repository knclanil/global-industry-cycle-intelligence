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

def build_unified_graph(layers, top_n, holdings=None, factor_markets=('Global','USA','India')):
    """Show both country and asset networks simultaneously; reuse shared company IDs."""
    nodes={'root':node('root','GLOBAL','root')}; edges=[]
    def add(n,parent):
        if n['id'] not in nodes:nodes[n['id']]=n
        if parent in nodes and (parent,n['id']) not in edges:edges.append((parent,n['id']))
    countries=layers.get('Countries',pd.DataFrame())
    if not countries.empty:
        preferred=countries[countries['ETF'].isin(['SPY','INDA','EUSA'])]
        selection=pd.concat([preferred,countries.nlargest(top_n,'Network Score')]).drop_duplicates('ETF').head(top_n+2)
        for _,r in selection.iterrows():
            add(node('country:'+str(r['ETF']),r['Sector'],'country','Countries',r),'root')
    for country_name,terms,asset_layer,sector_layer in [
        ('USA',('united states','usa','u.s.'),'USA Assets','USA Sectors'),
        ('India',('india',),'India Assets','India Sectors')]:
        matches=[n for n in nodes.values() if n['kind']=='country' and
                 (any(t in n['label'].lower() for t in terms) or
                  (country_name=='USA' and n['ticker'] in ('SPY','EUSA','IVV')))]
        if not matches:continue
        cid=matches[0]['id'];assets=layers.get(asset_layer,pd.DataFrame())
        if assets.empty:continue
        eq=assets[assets['Sector'].str.contains('Equit|Stock|Nifty',case=False,na=False)]
        for _,r in pd.concat([eq,assets.nlargest(top_n,'Network Score')]).drop_duplicates('ETF').head(top_n).iterrows():
            aid=f'{country_name}:asset:{r["ETF"]}'
            add(node(aid,r['Sector'],'asset',asset_layer,r),cid)
            if any(t in str(r['Sector']).lower() for t in ('equit','stock','nifty','s&p 500')):
                sector=layers.get(sector_layer,pd.DataFrame())
                if not sector.empty:
                    for _,sr in sector.nlargest(top_n,'Network Score').iterrows():
                        add(node(f'{country_name}:sector:{sr["ETF"]}',sr['Sector'],'sector',sector_layer,sr),aid)
    assets=layers.get('Global Assets',pd.DataFrame())
    if not assets.empty:
        eq=assets[assets['Sector'].str.contains('Equit|Stock',case=False,na=False)]
        for _,r in pd.concat([eq,assets.nlargest(top_n,'Network Score')]).drop_duplicates('ETF').head(top_n).iterrows():
            aid='global:asset:'+str(r['ETF'])
            add(node(aid,r['Sector'],'asset','Global Assets',r),'root')
            if not any(t in str(r['Sector']).lower() for t in ('equit','stock')):continue
            for market in factor_markets:
                factors=layers.get(market+' Factors',pd.DataFrame())
                if factors.empty:continue
                for _,f in factors.nlargest(top_n,'Network Score').iterrows():
                    fid=f'factor:{market}:{f["ETF"]}'
                    add(node(fid,f'{market} · {f["Sector"]}','factor',market+' Factors',f),aid)
                    if holdings is None or holdings.empty:continue
                    subset=holdings[holdings['factor'].astype(str).str.upper()==str(f['ETF']).upper()].nlargest(top_n,'weight')
                    for _,h in subset.iterrows():
                        identity=str(h.get('isin','')).strip() or str(h.get('ticker','')).strip() or str(h['company']).strip()
                        hid='company:'+market+':'+identity.upper()
                        add(node(hid,h['company'],'company'),fid)
    return nodes,edges


def layout(nodes,edges):
    """Stable, organic radial layout: countries left, asset classes right, shared companies outside."""
    import numpy as np
    from collections import defaultdict
    children=defaultdict(list)
    for a,b in edges:children[a].append(b)
    pos={'root':(0.,0.)}
    country_roots=sorted((x for x in children['root'] if nodes[x]['kind']=='country'))
    asset_roots=sorted((x for x in children['root'] if nodes[x]['kind']=='asset'))
    # Sector and factor descendants form radial clusters around their parent.
    def place_branch(nid,angle,radius,spread,depth=1):
        if nid in pos:return
        pos[nid]=(radius*math.cos(angle),radius*math.sin(angle))
        kids=[k for k in children[nid] if k not in pos]
        if not kids:return
        if len(kids)==1:angles=[angle]
        else:angles=np.linspace(angle-spread/2,angle+spread/2,len(kids))
        for k,a in zip(kids,angles):place_branch(k,float(a),radius+2.3,max(.26,spread*.70),depth+1)
    for i,nid in enumerate(country_roots):
        angle=math.pi-(i-(len(country_roots)-1)/2)*min(.45,2.1/max(1,len(country_roots)-1))
        place_branch(nid,angle,3.2,.42)
    for i,nid in enumerate(asset_roots):
        angle=(i-(len(asset_roots)-1)/2)*min(.40,2.3/max(1,len(asset_roots)-1))
        place_branch(nid,angle,3.2,.48)
    # Shared company nodes were already positioned at first factor; all edges remain visible.
    for nid in nodes:
        if nid not in pos:pos[nid]=(0.,0.)
    return pos


def make_figure(nodes,edges,selected=None):
    """Curved, translucent network edges and colored floating nodes, inspired by the supplied reference."""
    pos=layout(nodes,edges);fig=go.Figure()
    from collections import defaultdict
    segments=defaultdict(lambda: ([],[]))
    for a,b in edges:
        if a not in pos or b not in pos:continue
        x1,y1=pos[a];x2,y2=pos[b]
        dx=x2-x1;dy=y2-y1
        # Subtle curvature increases the organic appearance without implying fund flows.
        bend=.12*math.hypot(dx,dy)*(-1 if sum(ord(c) for c in b)%2 else 1)
        mx=(x1+x2)/2-bend*dy/(math.hypot(dx,dy)+1e-6)
        my=(y1+y2)/2+bend*dx/(math.hypot(dx,dy)+1e-6)
        group='selected' if selected in (a,b) else 'normal'
        xs,ys=segments[group]
        for i in range(13):
            t=i/12;xs.append((1-t)**2*x1+2*(1-t)*t*mx+t*t*x2)
            ys.append((1-t)**2*y1+2*(1-t)*t*my+t*t*y2)
        xs.append(None);ys.append(None)
    for group in ('normal','selected'):
        xs,ys=segments[group]
        if xs:fig.add_trace(go.Scattergl(x=xs,y=ys,mode='lines',line=dict(color='rgba(113,151,202,0.24)' if group=='normal' else 'rgba(180,225,255,0.85)',width=1 if group=='normal' else 2.5),hoverinfo='skip',showlegend=False))
    for kind in ('root','country','asset','sector','factor','company'):
        items=[n for n in nodes.values() if n['kind']==kind]
        if not items:continue
        fig.add_trace(go.Scattergl(
            x=[pos[n['id']][0] for n in items],y=[pos[n['id']][1] for n in items],
            mode='markers+text',
            text=[n['label'][:17]+'…' if len(n['label'])>18 else n['label'] for n in items],
            textposition='top center',textfont=dict(size=10,color='#d8e5f7'),
            marker=dict(size=[33 if n['id']==selected else (30 if kind=='root' else 12+min((n['score'] or 40)/8,13)) for n in items],
                        color=[COLORS.get(n['quadrant'],'#a1b3ce') if kind!='root' else '#a77cff' for n in items],
                        line=dict(color='#dbe9ff',width=1.1),opacity=.92),
            customdata=[[n['id']] for n in items],
            hovertemplate='%{text}<extra>'+kind.title()+'</extra>',name=kind.title(),showlegend=False))
    fig.update_layout(template='plotly_dark',paper_bgcolor='#0b1220',plot_bgcolor='#0b1220',
        height=780,margin=dict(l=12,r=12,t=12,b=12),dragmode='pan',clickmode='event+select',
        xaxis=dict(visible=False,scaleanchor='y',scaleratio=1),yaxis=dict(visible=False),
        uirevision='capital_organic_network',hovermode='closest')
    return fig

def render_capital_network():
    st.title('🌐 Global Capital Intelligence Network')
    st.caption('Organic market relationship network · **Not measured capital flows** · Click any node to inspect it')
    c1,c2,c3=st.columns([1.5,2.6,1.2])
    with c1:lookback=st.select_slider('RELATIVE TIME',options=list(country_market_data.LOOKBACKS),value='3M')
    with c2:period=st.date_input('FROM DATE → TO DATE',value=(date.today()-timedelta(days=365),date.today()),max_value=date.today())
    with c3:top_n=st.selectbox('TOP N PER CLUSTER',[3,5,10,20],index=1)
    with st.expander('Network filters & company holdings',expanded=False):
        factor_markets=st.multiselect('FACTOR MARKETS',['Global','USA','India'],default=['Global','USA','India'])
        st.caption('Company nodes require actual factor constituent weights. Upload CSV/XLSX containing factor, company, weight (%), and preferably ISIN/ticker. No synthetic company connections are generated.')
        uploaded=st.file_uploader('Factor holdings files',type=['csv','xlsx'],accept_multiple_files=True,key='network_holdings')
    if not isinstance(period,(tuple,list)) or len(period)!=2 or period[0]>=period[1]:
        st.info('Choose a valid start and end date.');return
    start,end=period
    holdings=None
    if uploaded:
        pieces=[]
        for file in uploaded:
            try:pieces.append(parse_holdings(file,source=file.name))
            except Exception as exc:st.warning(f'{file.name}: {exc}')
        if pieces:holdings=pd.concat(pieces,ignore_index=True)
    requested=['Countries','USA Assets','India Assets','USA Sectors','India Sectors','Global Assets']+[m+' Factors' for m in factor_markets]
    layers={};reports={};errors={}
    with st.spinner('Loading market data and constructing the network…'):
        for layer in requested:
            try:layers[layer],reports[layer]=fetch_layer(layer,start,end,lookback)
            except Exception as exc:errors[layer]=str(exc)
    if errors:
        with st.expander(f'Data availability: {len(errors)} unavailable layers'):
            for k,v in errors.items():st.warning(f'{k}: {v}')
    if not layers:
        st.error('No validated market data is available for the selected dates.');return
    nodes,edges=build_unified_graph(layers,top_n,holdings,factor_markets)
    selected=st.session_state.get('capital_selected')
    if selected not in nodes:selected=None
    event=st.plotly_chart(make_figure(nodes,edges,selected),use_container_width=True,
        key='capital_network_plot',on_select='rerun',selection_mode='points',
        config={'displaylogo':False,'scrollZoom':True,'modeBarButtonsToRemove':['lasso2d','select2d']})
    try:
        for point in event.selection.points:
            if point.get('customdata'):
                selected=point['customdata'][0];break
    except (AttributeError,KeyError,TypeError):pass
    if selected in nodes:st.session_state.capital_selected=selected
    if selected in nodes:
        n=nodes[selected]
        with st.expander('Selected node · '+n['label'],expanded=True):
            a,b,c,d=st.columns(4)
            a.metric('Node type',n['kind'].title())
            b.metric('Rotation score',f"{n['score']:.1f}/100" if n['score'] is not None else 'N/A')
            c.metric('Regime',n['quadrant'] or 'Not scored')
            d.metric('Period return',f"{n['return']:+.2f}%" if n['return'] is not None else 'N/A')
            neighbors=[nodes[t] for x,y in edges for t in ([y] if x==selected else [x] if y==selected else []) if t in nodes]
            if neighbors:st.dataframe(pd.DataFrame([{'Connected node':x['label'],'Type':x['kind'],'Rotation score':x['score']} for x in neighbors]),hide_index=True,use_container_width=True)
            if n['layer']:st.caption(f"Source: {n['layer']} · Symbol: {n['ticker']} · Relative strength: {n['relative']:+.2f}%")
    st.caption(f'{len(nodes)} nodes · {len(edges)} relationships · Green: Leading · Blue: Improving · Amber: Weakening · Red: Lagging. Scores are peer-relative and do not measure capital inflows.')
    if holdings is None:st.caption('Company connections are hidden until verified holdings are uploaded. Sector → company links also require sector constituent files.')
