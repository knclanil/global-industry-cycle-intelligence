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


def galaxy_layout(nodes, edges):
    """Seeded force-directed galaxy with country and global-asset hemispheres.

    Springs keep verified relationships connected; anchored hubs preserve the
    global-left/countries-right structure. Deterministic collision relaxation
    prevents the label pileups of a purely random spring layout.
    """
    import networkx as nx
    import numpy as np
    from collections import defaultdict, deque

    if not nodes:
        return {}
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from((a, b) for a, b in edges if a in nodes and b in nodes)
    children = defaultdict(list)
    parents = defaultdict(list)
    for a, b in edges:
        children[a].append(b)
        parents[b].append(a)

    # First place each branch in its own constellation. These positions are
    # starting points, not the final diagram: spring forces subsequently relax.
    seed = {'root': (0.0, 0.0)}
    fixed = ['root']
    if 'global:assets' in nodes:
        seed['global:assets'] = (-13.0, 0.0)
        fixed.append('global:assets')
    country_ids = [c for c in children['root'] if c != 'global:assets']
    detailed = [c for c in country_ids if children[c]]
    leaf = [c for c in country_ids if not children[c]]
    for i, cid in enumerate(detailed):
        y = (i - (len(detailed)-1)/2) * 24.0
        seed[cid] = (13.0, y)
        fixed.append(cid)
    for i, cid in enumerate(leaf):
        angle = 2 * math.pi * (i+.5) / max(1,len(leaf))
        seed[cid] = (8.0 + 5.0 * math.cos(angle), 14.0 * math.sin(angle))
    # Breadth-first placement keeps sector and factor constellations distinct.
    queue = deque(['root'])
    seen = {'root'}
    while queue:
        parent = queue.popleft()
        kids = children[parent]
        for j, kid in enumerate(kids):
            if kid not in seen:
                seen.add(kid)
                queue.append(kid)
            if kid in seed:
                continue
            px, py = seed.get(parent, (0.0, 0.0))
            market_global = parent.startswith('global:') or parent == 'global:assets'
            direction = -1 if market_global else 1
            offset = (j - (len(kids)-1)/2) * 3.5
            kind = nodes[kid]['kind']
            if kind == 'sector_group':
                offset -= 6.0
            elif kind == 'factor_group' and not market_global:
                offset += 6.0
            seed[kid] = (px + direction * 5.5, py + offset)
    # Shared companies start at the barycenter of all parent factors.
    for nid, item in nodes.items():
        if item['kind'] == 'company':
            coords = [seed[p] for p in parents[nid] if p in seed]
            if coords:
                seed[nid] = (sum(v[0] for v in coords)/len(coords) +
                             (-5 if any(p.startswith('factor:Global:') for p in parents[nid]) else 5),
                             sum(v[1] for v in coords)/len(coords))
    for nid in nodes:
        seed.setdefault(nid, (0.0, 0.0))
    if len(nodes) == 1:
        return seed

    # Spring physics create the organic web shown in the reference screenshot.
    positions = nx.spring_layout(
        graph, pos=seed, fixed=fixed, seed=29, iterations=130,
        k=3.7, scale=None, weight=None, threshold=1e-4,
    )
    coords = {nid: np.array(positions[nid], dtype=float) for nid in nodes}
    # Keep the global asset system to the left, countries to the right.
    for _ in range(75):
        moved = False
        for i, a in enumerate(nodes):
            if a in fixed:
                continue
            for b in list(nodes)[i+1:]:
                if b in fixed:
                    continue
                delta = coords[b]-coords[a]
                dist = float(np.linalg.norm(delta))
                # Include a modest text-label allowance as well as planet radius.
                ra = 1.0 + min(len(nodes[a]['label']), 20)*.055
                rb = 1.0 + min(len(nodes[b]['label']), 20)*.055
                gap = ra + rb + .55
                if dist >= gap:
                    continue
                if dist < 1e-7:
                    angle = ((i * 37 + len(b) * 19) % 360) * math.pi/180
                    delta = np.array([math.cos(angle),math.sin(angle)])
                    dist = 1.0
                shift = (gap-dist) * .53 * delta/dist
                coords[a] -= shift
                coords[b] += shift
                moved = True
        if not moved:
            break
    return {nid: tuple(map(float, xy)) for nid, xy in coords.items()}


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


def make_figure(nodes, edges, selected=None):
    """Midnight-cosmos styling: layered luminous planets, restrained stars, and thin arcs.

    Scores affect diameter only; colors still represent the original quadrants.
    The star field is decorative and does not encode market observations.
    """
    import random
    from collections import defaultdict

    pos = galaxy_layout(nodes, edges)
    fig = go.Figure()
    if not pos:
        return fig

    xvals = [xy[0] for xy in pos.values()]
    yvals = [xy[1] for xy in pos.values()]
    xmin, xmax = min(xvals), max(xvals)
    ymin, ymax = min(yvals), max(yvals)
    xpad = max(5, (xmax - xmin) * .11)
    ypad = max(5, (ymax - ymin) * .12)
    xr = (xmin-xpad, xmax+xpad)
    yr = (ymin-ypad, ymax+ypad)

    # A subtle, seeded star field, visually behind the network and not selectable.
    rng = random.Random(71)
    stars_x, stars_y, stars_size = [], [], []
    for _ in range(160):
        stars_x.append(rng.uniform(*xr))
        stars_y.append(rng.uniform(*yr))
        stars_size.append(rng.choice([.7, .9, 1.1, 1.5]))
    fig.add_trace(go.Scattergl(x=stars_x, y=stars_y, mode='markers',
        marker=dict(size=stars_size, color='rgba(171,193,229,0.23)'),
        hoverinfo='skip', showlegend=False))

    connected = {selected} if selected else set()
    if selected:
        for a,b in edges:
            if selected == a: connected.add(b)
            if selected == b: connected.add(a)

    segments = defaultdict(lambda: ([], []))
    for a,b in edges:
        if a not in pos or b not in pos: continue
        x1,y1 = pos[a]; x2,y2 = pos[b]
        dx,dy = x2-x1,y2-y1
        dist = math.hypot(dx,dy)
        bend = .095 * dist * (-1 if sum(map(ord,b)) % 2 else 1)
        mx = (x1+x2)/2 - bend*dy/(dist+1e-9)
        my = (y1+y2)/2 + bend*dx/(dist+1e-9)
        group = 'active' if selected in (a,b) else 'dim' if selected else 'normal'
        xs,ys = segments[group]
        for j in range(17):
            t=j/16
            xs.append((1-t)**2*x1+2*(1-t)*t*mx+t*t*x2)
            ys.append((1-t)**2*y1+2*(1-t)*t*my+t*t*y2)
        xs.append(None);ys.append(None)
    for group in ('dim','normal','active'):
        xs,ys=segments[group]
        if not xs:continue
        color={'dim':'rgba(97,124,165,0.09)','normal':'rgba(114,153,196,0.26)',
               'active':'rgba(173,218,255,0.80)'}[group]
        fig.add_trace(go.Scattergl(x=xs,y=ys,mode='lines',
            line=dict(color=color,width=2.2 if group=='active' else .85),
            hoverinfo='skip',showlegend=False))

    kinds=('root','country','asset_group','asset','equity','sector_group',
           'factor_group','sector','factor','company')
    for kind in kinds:
        items=[n for n in nodes.values() if n['kind']==kind]
        if not items:continue
        xs=[pos[n['id']][0] for n in items]
        ys=[pos[n['id']][1] for n in items]
        sizes=[48 if kind=='root' else
               (13+29*math.sqrt(max(0,min(100,n['score']))/100)
                if n['score'] is not None else 19) for n in items]
        colors=[('#a98bff' if kind=='root' else
                 COLORS.get(n['quadrant'],'#7892b2')) for n in items]
        opacity=[1 if not selected or n['id'] in connected else .28 for n in items]
        # Three concentric layers produce a planet-like illuminated disc.
        for multiplier,alpha in ((1.72,.085),(1.35,.16)):
            fig.add_trace(go.Scattergl(x=xs,y=ys,mode='markers',
                marker=dict(size=[v*multiplier for v in sizes],color=colors,
                            opacity=[alpha*o for o in opacity],line=dict(width=0)),
                hoverinfo='skip',showlegend=False))
        fig.add_trace(go.Scattergl(x=xs,y=ys,mode='markers',
            marker=dict(size=sizes,color=colors,opacity=opacity,
                        line=dict(color='rgba(225,239,255,0.80)',width=1.15)),
            customdata=[[n['id']] for n in items],
            hovertext=[f"{n['label']}<br>Score: {n['score']:.1f}/100" if n['score'] is not None
                       else f"{n['label']}<br>Structural node · not scored" for n in items],
            hovertemplate='%{hovertext}<extra></extra>',
            showlegend=False))
        # Small, displaced specular highlights make circles read as planets.
        fig.add_trace(go.Scattergl(x=[x-.10 for x in xs],y=[y+.10 for y in ys],
            mode='markers',marker=dict(size=[max(2,v*.13) for v in sizes],
                color='rgba(245,250,255,0.38)',opacity=opacity),
            hoverinfo='skip',showlegend=False))
        labels=[n['label'] if len(n['label'])<=21 else n['label'][:19]+'…' for n in items]
        fig.add_trace(go.Scattergl(x=xs,y=ys,mode='text',text=labels,
            textposition='top center',textfont=dict(size=11 if kind in ('root','country','equity') else 9,
                color='#dce8fa'),opacity=opacity,hoverinfo='skip',showlegend=False))

    fig.update_layout(template='plotly_dark',paper_bgcolor='#070d1b',
        plot_bgcolor='#070d1b',height=890,
        margin=dict(l=12,r=12,t=12,b=12),dragmode='pan',clickmode='event+select',
        xaxis=dict(visible=False,range=xr,scaleanchor='y',scaleratio=1,
                   showgrid=False,zeroline=False),
        yaxis=dict(visible=False,range=yr,showgrid=False,zeroline=False),
        uirevision='capital_cosmos_v3',hovermode='closest',
        font=dict(color='#dce8fa'))
    return fig

def render_capital_network():
    st.title('🌌 Global Capital Intelligence Galaxy')
    st.caption('Midnight Cosmos · luminous score-sized planets · country and global asset galaxies · connections show relationships, not measured fund flows')
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
