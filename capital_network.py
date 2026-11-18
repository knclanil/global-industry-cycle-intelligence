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

def build_unified_graph(layers, top_n, holdings=None, factor_markets=('USA', 'India')):
    """One rooted hierarchy: Global → Country → Assets → Equity → Sectors | Factors.

    Only USA and India currently have country-specific asset, sector and factor feeds.
    All other countries terminate at the country node; no invented proxy branches.
    """
    nodes={'root':node('root','GLOBAL','root')}; edges=[]
    def add(item,parent):
        if item['id'] not in nodes: nodes[item['id']]=item
        if parent in nodes and (parent,item['id']) not in edges:edges.append((parent,item['id']))
    countries=layers.get('Countries',pd.DataFrame())
    if countries.empty:
        countries=pd.DataFrame(columns=['ETF','Sector','Network Score'])
    # Always retain USA and India if their country observations exist.
    preferred=countries[countries['ETF'].isin(['SPY','INDA'])]
    chosen=pd.concat([preferred,countries.nlargest(top_n,'Network Score')]).drop_duplicates('ETF').head(top_n+2)
    specs={'SPY':('USA','USA Assets','USA Sectors','USA Factors'),
           'INDA':('India','India Assets','India Sectors','India Factors')}
    for _,country in chosen.iterrows():
        ticker=str(country['ETF']); cid='country:'+ticker
        add(node(cid,country['Sector'],'country','Countries',country),'root')
        if ticker not in specs:continue
        market,asset_layer,sector_layer,factor_layer=specs[ticker]
        assets=layers.get(asset_layer,pd.DataFrame())
        if assets.empty:continue
        group=market+':assets';add(node(group,'ASSETS','asset_group'),cid)
        # Include equity first even when its rotation score is low; then other assets.
        eq=assets[assets['Sector'].str.contains('Equit|Stock|Nifty',case=False,na=False)]
        other=assets[~assets['ETF'].isin(eq['ETF'])]
        chosen_assets=pd.concat([eq,other.nlargest(max(top_n-1,0),'Network Score')]).drop_duplicates('ETF')
        for _,asset in chosen_assets.iterrows():
            equity=str(asset['ETF']) in set(eq['ETF'])
            aid=f'{market}:asset:{asset["ETF"]}'
            add(node(aid,'Equity' if equity else asset['Sector'],'equity' if equity else 'asset',asset_layer,asset),group)
            if not equity:continue
            # Both vertical groups are children of THIS country's equity, never GLOBAL.
            sg=f'{market}:sectors';fg=f'{market}:factors'
            add(node(sg,'SECTORS','sector_group'),aid)
            add(node(fg,'FACTORS','factor_group'),aid)
            sector_rows=layers.get(sector_layer,pd.DataFrame())
            if not sector_rows.empty:
                for _,row in sector_rows.nlargest(top_n,'Network Score').iterrows():
                    add(node(f'{market}:sector:{row["ETF"]}',row['Sector'],'sector',sector_layer,row),sg)
            factor_rows=layers.get(factor_layer,pd.DataFrame()) if market in factor_markets else pd.DataFrame()
            if not factor_rows.empty:
                for _,row in factor_rows.nlargest(top_n,'Network Score').iterrows():
                    fid=f'factor:{market}:{row["ETF"]}'
                    add(node(fid,row['Sector'],'factor',factor_layer,row),fg)
                    if holdings is None or holdings.empty:continue
                    matches=holdings[holdings['factor'].astype(str).str.upper()==str(row['ETF']).upper()]
                    for _,h in matches.nlargest(top_n,'weight').iterrows():
                        isin=str(h.get('isin','')).strip().upper()
                        tick=str(h.get('ticker','')).strip().upper()
                        identity=('isin:'+isin if isin and isin not in ('NAN','NONE') else
                                  'ticker:'+market+':'+tick if tick and tick not in ('NAN','NONE') else
                                  'name:'+market+':'+str(h['company']).strip().upper())
                        add(node('company:'+identity,h['company'],'company'),fid)
    # Independent global asset system, opposite the country system.
    # Only validated global asset/factor observations create scored nodes.
    global_assets=layers.get('Global Assets',pd.DataFrame())
    if not global_assets.empty:
        group='global:assets'
        add(node(group,'GLOBAL ASSETS','asset_group'),'root')
        eq=global_assets[global_assets['Sector'].astype(str).str.contains('Equit|Stock',case=False,na=False)]
        other=global_assets[~global_assets['ETF'].isin(eq['ETF'])]
        chosen_global=pd.concat([eq,other.nlargest(max(top_n-1,0),'Network Score')]).drop_duplicates('ETF')
        for _,asset in chosen_global.iterrows():
            equity=str(asset['ETF']) in set(eq['ETF'])
            aid='global:asset:'+str(asset['ETF'])
            add(node(aid,'Equity' if equity else asset['Sector'],'equity' if equity else 'asset','Global Assets',asset),group)
            if not equity:continue
            fg='global:factors'
            add(node(fg,'FACTORS','factor_group'),aid)
            factors=layers.get('Global Factors',pd.DataFrame())
            if factors.empty:continue
            for _,f in factors.nlargest(top_n,'Network Score').iterrows():
                fid='factor:Global:'+str(f['ETF'])
                add(node(fid,f['Sector'],'factor','Global Factors',f),fg)
                if holdings is None or holdings.empty:continue
                matches=holdings[holdings['factor'].astype(str).str.upper()==str(f['ETF']).upper()]
                for _,h in matches.nlargest(top_n,'weight').iterrows():
                    isin=str(h.get('isin','')).strip().upper()
                    tick=str(h.get('ticker','')).strip().upper()
                    identity=('isin:'+isin if isin and isin not in ('NAN','NONE') else
                              'ticker:Global:'+tick if tick and tick not in ('NAN','NONE') else
                              'name:Global:'+str(h['company']).strip().upper())
                    add(node('company:'+identity,h['company'],'company'),fid)
    return nodes,edges


def galaxy_layout(nodes,edges):
    """Deterministic bilateral orbital layout: global assets left, countries right.

    A tree layout per hemisphere ensures the root and each cluster retain their
    hierarchy. Company nodes are placed on an outer ring, shared where possible.
    """
    from collections import defaultdict
    children=defaultdict(list)
    parents=defaultdict(list)
    for a,b in edges:
        children[a].append(b);parents[b].append(a)
    pos={'root':(0.0,0.0)}
    global_group='global:assets'
    if global_group in nodes:
        pos[global_group]=(-10.0,0.0)
        assets=children[global_group]
        for i,aid in enumerate(assets):
            theta=math.pi/2+(i-(len(assets)-1)/2)*0.39
            pos[aid]=(-14.0-2.8*math.sin(theta), (i-(len(assets)-1)/2)*3.0)
            for branch in children[aid]:
                pos[branch]=(-20.0,pos[aid][1])
                for j,fid in enumerate(children[branch]):
                    pos[fid]=(-25.0,pos[branch][1]+(j-(len(children[branch])-1)/2)*2.45)
    countries=children['root']
    country_ids=[cid for cid in countries if cid!=global_group]
    detailed=[cid for cid in country_ids if children[cid]]
    leaves=[cid for cid in country_ids if not children[cid]]
    # Detailed countries receive independent vertical systems.
    for i,cid in enumerate(detailed):
        cy=(i-(len(detailed)-1)/2)*27.0
        pos[cid]=(9.0,cy)
        for group in children[cid]:
            pos[group]=(13.0,cy)
            assets=children[group]
            equity=[a for a in assets if nodes[a]['kind']=='equity']
            other=[a for a in assets if nodes[a]['kind']!='equity']
            for j,aid in enumerate(other):
                pos[aid]=(16.5,cy+5.0+(j-(len(other)-1)/2)*2.7)
            for aid in equity:
                pos[aid]=(18.0,cy-3.0)
                for branch in children[aid]:
                    sector=nodes[branch]['kind']=='sector_group'
                    by=cy-11.0 if sector else cy+1.0
                    pos[branch]=(23.0,by)
                    kids=children[branch]
                    for k,kid in enumerate(kids):
                        pos[kid]=(28.0,by+(k-(len(kids)-1)/2)*2.4)
    # Country-only observations orbit closer to the root to avoid a long tail.
    for j,cid in enumerate(leaves):
        a=(j+0.5)*2*math.pi/max(len(leaves),1)
        pos[cid]=(7.5+2.0*math.cos(a), 12.0*math.sin(a))
    # Companies are outer satellites; multi-factor edges converge on one node.
    companies=[nid for nid,n in nodes.items() if n['kind']=='company']
    for market in ('Global','USA','India'):
        subset=[cid for cid in companies if any(p.startswith('factor:'+market+':') for p in parents[cid])]
        for j,cid in enumerate(subset):
            ps=[pos[p] for p in parents[cid] if p in pos]
            mean_y=sum(p[1] for p in ps)/len(ps) if ps else 0.0
            pos[cid]=(-30.0 if market=='Global' else 34.0,mean_y+(j-(len(subset)-1)/2)*1.6)
    for nid in nodes:pos.setdefault(nid,(0.,0.))
    return pos


def layout(nodes,edges):
    """Country lanes with visibly distinct left SECTORS and right FACTORS columns.

    Asset siblings sit above the equity branches; company nodes share IDs and
    remain connected to all their parent factors without duplicating entities.
    """
    from collections import defaultdict
    children=defaultdict(list)
    for a,b in edges:children[a].append(b)
    pos={'root':(0.,3.)}
    countries=children['root']
    detailed=[c for c in countries if children[c]]
    leaves=[c for c in countries if not children[c]]
    # Give USA/India large independent lanes, rather than overlapping clusters.
    lane_width=23.0
    for i,cid in enumerate(detailed):
        cx=(i-(len(detailed)-1)/2)*lane_width
        pos[cid]=(cx,0.)
        for group in children[cid]:
            pos[group]=(cx,-2.4)
            assets=children[group]
            equity=[a for a in assets if nodes[a]['kind']=='equity']
            others=[a for a in assets if nodes[a]['kind']!='equity']
            for j,aid in enumerate(others):
                pos[aid]=(cx+(j-(len(others)-1)/2)*3.1,-4.7)
            for aid in equity:
                pos[aid]=(cx,-7.0)
                for branch in children[aid]:
                    sector=nodes[branch]['kind']=='sector_group'
                    bx=cx+(-5.6 if sector else 5.6)
                    pos[branch]=(bx,-9.7)
                    kids=children[branch]
                    for k,kid in enumerate(kids):
                        pos[kid]=(bx,-12.2-2.25*k)
    # Countries without validated asset layers remain clearly visible, as leaves.
    for j,cid in enumerate(leaves):
        x=(j-(len(leaves)-1)/2)*4.2
        pos[cid]=(x, -3.0)
    # Shared company IDs: one node per company, multiple factor edges.
    parents=defaultdict(list)
    for a,b in edges:parents[b].append(a)
    company_ids=[nid for nid,n in nodes.items() if n['kind']=='company']
    company_groups=defaultdict(list)
    for cid in company_ids:
        ps=[pos[p] for p in parents[cid] if p in pos]
        market='USA' if any(p.startswith('factor:USA:') for p in parents[cid]) else 'India'
        company_groups[market].append((cid,ps))
    for market,items in company_groups.items():
        for j,(cid,ps) in enumerate(items):
            x=sum(p[0] for p in ps)/len(ps)+3.6 if ps else 0.
            pos[cid]=(x,-13.5-2.0*j)
    for nid in nodes:
        pos.setdefault(nid,(0.,-1.))
    return pos


def make_figure(nodes,edges,selected=None):
    """Curved, translucent network edges and colored floating nodes, inspired by the supplied reference."""
    pos=galaxy_layout(nodes,edges);fig=go.Figure()
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
    for kind in ('root','country','asset_group','asset','equity','sector_group','factor_group','sector','factor','company'):
        items=[n for n in nodes.values() if n['kind']==kind]
        if not items:continue
        fig.add_trace(go.Scattergl(
            x=[pos[n['id']][0] for n in items],y=[pos[n['id']][1] for n in items],
            mode='markers+text',
            text=[n['label'][:17]+'…' if len(n['label'])>18 else n['label'] for n in items],
            textposition='top center',textfont=dict(size=10,color='#d8e5f7'),
            marker=dict(size=[42 if kind=='root' else (12+31*math.sqrt(max(0.,min(100.,n['score']))/100.) if n['score'] is not None else 16) + (5 if n['id']==selected else 0) for n in items],
                        color=[COLORS.get(n['quadrant'],'#a1b3ce') if kind!='root' else '#a77cff' for n in items],
                        line=dict(color='#dbe9ff',width=1.1),opacity=.92),
            customdata=[[n['id']] for n in items],
            hovertemplate='%{text}<extra>'+kind.title()+'</extra>',name=kind.title(),showlegend=False))
    fig.update_layout(template='plotly_dark',paper_bgcolor='#0b1220',plot_bgcolor='#0b1220',
        height=850,margin=dict(l=12,r=12,t=12,b=12),dragmode='pan',clickmode='event+select',
        xaxis=dict(visible=False,scaleanchor='y',scaleratio=1),yaxis=dict(visible=False),
        uirevision='capital_galaxy_v1',hovermode='closest')
    return fig

def render_capital_network():
    st.title('🌌 Global Capital Intelligence Galaxy')
    st.caption('Left: Global → Assets → Equity → Factors · Right: Global → Countries → Assets → Equity → Sectors | Factors · Planet size = score (not measured capital flows)')
    c1,c2,c3=st.columns([1.5,2.6,1.2])
    with c1:lookback=st.select_slider('RELATIVE TIME',options=list(country_market_data.LOOKBACKS),value='3M')
    with c2:period=st.date_input('FROM DATE → TO DATE',value=(date.today()-timedelta(days=365),date.today()),max_value=date.today())
    with c3:top_n=st.selectbox('TOP N PER CLUSTER',[3,5,10,20],index=1)
    with st.expander('Network filters & company holdings',expanded=False):
        factor_markets=st.multiselect('COUNTRY FACTOR DATA',['USA','India'],default=['USA','India'])
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
    requested=['Countries','Global Assets','Global Factors','USA Assets','India Assets','USA Sectors','India Sectors']+[m+' Factors' for m in factor_markets if m in ('USA','India')]
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
    st.caption(f'{len(nodes)} planets · {len(edges)} relationships · Green: Leading · Blue: Improving · Amber: Weakening · Red: Lagging. Scores are peer-relative and do not measure capital inflows.')
    if holdings is None:st.caption('Factor → company connections require uploaded constituent weights. Sector → company connections require separate verified sector constituents. Other countries show country scores only until country asset data is available.')
