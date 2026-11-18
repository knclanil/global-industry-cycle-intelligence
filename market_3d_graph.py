"""Responsive hierarchical 2D market knowledge graph, no constituent companies."""
import json
from datetime import date, timedelta
import streamlit as st
import streamlit.components.v1 as components

SOURCE_GROUPS = ['Countries','USA Assets','India Assets','Global Assets','USA Sectors','India Sectors','Global Sectors','USA Factors','India Factors','Global Factors']

def graph_payload(layers):
    nodes=[dict(id='global',label='GLOBAL',kind='root',parent=None,score=None)]
    seen={'global'}
    def add(id,label,kind,parent,score=None,ticker=None):
        if id in seen:return
        seen.add(id);nodes.append(dict(id=id,label=str(label),kind=kind,parent=parent,score=score,ticker=ticker))
    add('countries','Countries','group','global')
    add('global-sectors','Global Sectors','group','global')
    add('global-factors','Global Factors','group','global')
    def entries(source):
        frame=layers.get(source)
        if frame is None or frame.empty:return []
        return frame.to_dict('records')
    def score(r):
        try:return max(0,min(100,float(r['Network Score'])))
        except (TypeError,ValueError,KeyError):return None
    def label(r):return str(r.get('Sector') or r.get('ETF') or 'Unknown')
    def leaf(r,parent,source):
        ticker=str(r.get('ETF','')).strip()
        if ticker:add('etf:'+source+':'+ticker, ticker+' · '+label(r),'etf',parent,score(r),ticker)
    for typ,source in [('sector','Global Sectors'),('factor','Global Factors')]:
        parent='global-sectors' if typ=='sector' else 'global-factors'
        for r in entries(source):
            ticker=str(r.get('ETF','')).strip()
            ident=typ+':global:'+ticker
            add(ident,label(r),typ,parent,score(r))
            leaf(r,ident,source)
    country_records=entries('Countries')
    for r in country_records:
        ticker=str(r.get('ETF','')).strip()
        name=label(r)
        cid='country:'+ticker
        add(cid,name,'country','countries',score(r),ticker)
    # Only countries with dedicated country asset feeds receive further branches.
    for country,terms,asset_source,sector_source,factor_source in [
        ('USA',('united states','usa','u.s.'),'USA Assets','USA Sectors','USA Factors'),
        ('India',('india',),'India Assets','India Sectors','India Factors')]:
        matches=[n for n in nodes if n['kind']=='country' and any(t in n['label'].lower() for t in terms)]
        if not matches:
            # A country cannot be inferred from an arbitrary country proxy.
            continue
        cid=matches[0]['id'];assets='assets:'+country
        add(assets,'Asset Classes','group',cid)
        records=entries(asset_source)
        equity=[];bond=[];cash=[];other=[]
        for r in records:
            text=label(r).lower()
            if any(x in text for x in ('equit','stock','nifty','s&p 500','large cap','small cap')):equity.append(r)
            elif any(x in text for x in ('bond','treasury','fixed income','government debt','corporate debt')):bond.append(r)
            elif any(x in text for x in ('cash','t-bill','bill','money market','ultra-short','ultrashort')):cash.append(r)
            else:other.append(r)
        for name,group in [('Equity',equity),('Bonds',bond),('Cash',cash),('Other Assets',other)]:
            if not group and name=='Other Assets':continue
            scores=[score(r) for r in group if score(r) is not None]
            aid='asset:'+country+':'+name
            add(aid,name,'asset',assets,round(sum(scores)/len(scores),1) if scores else None)
            if name=='Equity':
                for typ,source in [('Sectors',sector_source),('Factors',factor_source)]:
                    pid='branch:'+country+':'+typ
                    add(pid,typ,'group',aid)
                    for r in entries(source):
                        ticker=str(r.get('ETF','')).strip()
                        sid='strategy:'+country+':'+typ+':'+ticker
                        add(sid,label(r),'sector' if typ=='Sectors' else 'factor',pid,score(r))
                        leaf(r,sid,source)
            else:
                for r in group:leaf(r,aid,asset_source)
    return {'nodes':nodes}

HTML=r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}html,body{margin:0;background:#050608;color:#f0f0f0;font-family:system-ui,Arial,sans-serif}#app{position:relative;height:740px;width:100%;background:#050608;border:1px solid #25282d;border-radius:12px;overflow:hidden}svg{width:100%;height:100%;touch-action:none;cursor:grab}svg:active{cursor:grabbing}line{stroke:#6a6c73;stroke-opacity:.48;stroke-width:1.25}circle{fill:#a6a8ac;stroke:#f1f1f1;stroke-opacity:.85;stroke-width:1.2;cursor:pointer}circle:hover{fill:#fff}.node-label{fill:#e7e9ed;font:12px system-ui,Arial,sans-serif;paint-order:stroke;stroke:#050608;stroke-width:3px;stroke-linejoin:round;pointer-events:none}.node-label.root-label{font-weight:700;font-size:14px}#bar{position:absolute;top:12px;left:12px;right:12px;display:flex;flex-wrap:wrap;gap:8px;z-index:2;pointer-events:none}button,input{pointer-events:auto;border:1px solid #444952;background:#14171c;color:white;border-radius:7px;padding:9px;font:13px system-ui}button{cursor:pointer}input{min-width:160px;max-width:240px;flex:1}#tip{display:none;position:absolute;pointer-events:none;background:#1b1e24;border:1px solid #62666d;border-radius:8px;padding:10px 13px;font-size:13px;z-index:4;max-width:290px;box-shadow:0 6px 30px #0009}#tip strong{display:block;font-size:15px;margin-bottom:5px}#note{position:absolute;bottom:10px;left:12px;color:#9b9ea6;font-size:12px;pointer-events:none}#empty{position:absolute;top:65px;left:15px;color:#b7bbc2;font-size:12px} @media(max-width:600px){#app{height:610px}button,input{font-size:12px;padding:7px}#note{font-size:10px}}
</style></head><body><div id="app"><div id="bar"><input id="search" placeholder="Find a country, asset, sector, factor, ETF" aria-label="Find node"><button id="fit">Auto fit</button><button id="open">Expand all</button><button id="close">Collapse</button><button id="plus">+</button><button id="minus">−</button></div><svg id="svg" aria-label="Expandable hierarchical market knowledge graph"><g id="view"><g id="lines"></g><g id="dots"></g></g></svg><div id="tip"></div><div id="note">Click circles to expand · Labels show names · Hover for full details · Drag to pan · Scroll to zoom</div></div><script>
(()=>{'use strict';const data=__PAYLOAD__,items=new Map(data.nodes.map(n=>[n.id,n])),children=new Map(),parent=new Map();for(const n of data.nodes){if(n.parent){if(!children.has(n.parent))children.set(n.parent,[]);children.get(n.parent).push(n.id);parent.set(n.id,n.parent)}}const svg=document.getElementById('svg'),view=document.getElementById('view'),dots=document.getElementById('dots'),lines=document.getElementById('lines'),tip=document.getElementById('tip'),app=document.getElementById('app');const NS='http://www.w3.org/2000/svg';let expanded=new Set(['global']),scale=1,tx=0,ty=0,positions=new Map(),drag=false,oldX=0,oldY=0;function el(tag,attrs){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs||{}))e.setAttribute(k,v);return e}function visible(){const result=[];function walk(id,depth){result.push({id,depth});if(expanded.has(id))for(const c of children.get(id)||[])walk(c,depth+1)}walk('global',0);return result}function radius(n){const w=svg.clientWidth||900,h=svg.clientHeight||700;const responsive=Math.max(.72,Math.min(1.3,Math.sqrt(w*h/(1100*740))));const density=Math.max(.7,Math.min(1,Math.sqrt(35/Math.max(visible().length,1))));return (n.score===null||n.score===undefined?9:6+Math.sqrt(Math.max(0,n.score)/100)*17)*responsive*density}function layout(rows){const byDepth=new Map();for(const row of rows){if(!byDepth.has(row.depth))byDepth.set(row.depth,[]);byDepth.get(row.depth).push(row.id)}const maxDepth=Math.max(...byDepth.keys()),w=svg.clientWidth||900,h=svg.clientHeight||740;const dx=Math.max(210,Math.min(290,w/Math.max(2,maxDepth+1)));const coords=new Map();let nextY=0;function assign(id,depth){const kids=(expanded.has(id)?children.get(id)||[]:[]).filter(k=>rows.some(x=>x.id===k));if(!kids.length){coords.set(id,[depth*dx,nextY*65]);nextY++;return}for(const k of kids)assign(k,depth+1);const ys=kids.map(k=>coords.get(k)[1]);coords.set(id,[depth*dx,(Math.min(...ys)+Math.max(...ys))/2])}assign('global',0);return coords}function transform(){view.setAttribute('transform',`translate(${tx} ${ty}) scale(${scale})`)}function fit(){const rows=visible();positions=layout(rows);const xs=[...positions.values()].map(p=>p[0]),ys=[...positions.values()].map(p=>p[1]);const minX=Math.min(...xs)-45,maxX=Math.max(...xs)+210,minY=Math.min(...ys)-40,maxY=Math.max(...ys)+40;const w=svg.clientWidth,h=svg.clientHeight;scale=Math.min(1.7,Math.max(.12,Math.min((w-55)/(maxX-minX||1),(h-125)/(maxY-minY||1))));tx=w/2-scale*(minX+maxX)/2;ty=h/2-scale*(minY+maxY)/2;transform()}function showTip(e,n){tip.style.display='block';tip.innerHTML='';const title=document.createElement('strong');title.textContent=n.label;tip.append(title);const text=document.createElement('div');text.textContent=(n.score===null||n.score===undefined?'Performance: unavailable':'Performance: '+n.score.toFixed(1)+'/100')+' · Circle diameter: '+Math.round(radius(n)*2)+' px'+(n.ticker?' · ETF: '+n.ticker:'');tip.append(text);const r=app.getBoundingClientRect();tip.style.left=Math.max(8,Math.min(e.clientX-r.left+15,r.width-305))+'px';tip.style.top=Math.max(58,Math.min(e.clientY-r.top+12,r.height-95))+'px'}function draw(refit=true){tip.style.display='none';dots.replaceChildren();lines.replaceChildren();const rows=visible(),ids=new Set(rows.map(r=>r.id));positions=layout(rows);for(const n of data.nodes){if(!ids.has(n.id)||!n.parent||!ids.has(n.parent))continue;const [x1,y1]=positions.get(n.parent),[x2,y2]=positions.get(n.id);lines.append(el('line',{x1,y1,x2,y2}))}for(const row of rows){const n=items.get(row.id),[x,y]=positions.get(n.id),g=el('g',{transform:`translate(${x} ${y})`,tabindex:'0',role:'button','aria-label':n.label}),circle=el('circle',{r:radius(n)});g.append(circle);const label=el('text',{x:radius(n)+9,y:4,class:'node-label'+(n.kind==='root'?' root-label':'')});const full=n.label||n.id;const maxChars=(svg.clientWidth<620?19:29);label.textContent=full.length>maxChars?full.slice(0,maxChars-1)+'…':full;const fullTitle=el('title');fullTitle.textContent=full;label.append(fullTitle);g.append(label);g.addEventListener('mouseenter',e=>showTip(e,n));g.addEventListener('mousemove',e=>showTip(e,n));g.addEventListener('mouseleave',()=>tip.style.display='none');const click=()=>{if(!children.has(n.id))return;expanded.has(n.id)?expanded.delete(n.id):expanded.add(n.id);draw(true)};g.addEventListener('click',click);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();click()}});dots.append(g)}if(refit)fit()}document.getElementById('fit').onclick=fit;document.getElementById('open').onclick=()=>{expanded=new Set(data.nodes.map(n=>n.id));draw()};document.getElementById('close').onclick=()=>{expanded=new Set(['global']);draw()};function zoom(f){scale=Math.max(.1,Math.min(5,scale*f));transform()}document.getElementById('plus').onclick=()=>zoom(1.25);document.getElementById('minus').onclick=()=>zoom(.8);document.getElementById('search').oninput=e=>{const q=e.target.value.toLowerCase().trim();if(!q)return;const n=data.nodes.find(n=>n.label.toLowerCase().includes(q)||(n.ticker||'').toLowerCase().includes(q));if(!n)return;let p=n.parent;while(p){expanded.add(p);p=parent.get(p)}draw();const xy=positions.get(n.id);if(xy){tx=svg.clientWidth/2-xy[0]*scale;ty=svg.clientHeight/2-xy[1]*scale;transform()}};svg.addEventListener('pointerdown',e=>{if(e.target.closest('g[role="button"]'))return;drag=true;oldX=e.clientX;oldY=e.clientY;svg.setPointerCapture(e.pointerId)});svg.addEventListener('pointermove',e=>{if(!drag)return;tx+=e.clientX-oldX;ty+=e.clientY-oldY;oldX=e.clientX;oldY=e.clientY;transform()});svg.addEventListener('pointerup',()=>drag=false);svg.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY<0?1.12:.89)},{passive:false});let timer;new ResizeObserver(()=>{clearTimeout(timer);timer=setTimeout(()=>draw(true),140)}).observe(svg);draw()})();
</script></body></html>'''

def render():
    from capital_network import fetch_layer
    import country_market_data
    st.title('Global Market Intelligence · Knowledge Graph')
    st.caption('Global → Countries → Assets → Equity / Bonds / Cash; plus independent Global Sectors and Global Factors. Circle area indicates relative performance; no companies or holdings.')
    a,b=st.columns(2)
    with a: lookback=st.select_slider('Relative strength period',options=list(country_market_data.LOOKBACKS),value='3M')
    with b: period=st.date_input('Observation dates',value=(date.today()-timedelta(days=365),date.today()),max_value=date.today())
    if not isinstance(period,(tuple,list)) or len(period)!=2 or period[0]>=period[1]:
        st.info('Select a valid start and end date.');return
    layers,errors={},{}
    with st.spinner('Loading market observations…'):
        for source in SOURCE_GROUPS:
            try:layers[source],_=fetch_layer(source,period[0],period[1],lookback)
            except Exception as exc:errors[source]=str(exc)
    payload=graph_payload(layers)
    st.caption(f"{len(payload['nodes'])} available graph nodes · Click to expand branches · Labels show names · Hover to inspect scores")
    components.html(HTML.replace('__PAYLOAD__',json.dumps(payload).replace('</','<\\/')),height=760,scrolling=False)
    if errors:
        with st.expander(f'Unavailable data sources ({len(errors)})'):
            for name,error in errors.items():st.caption(f'{name}: {error}')
    st.caption('Country branches are shown only where country-specific sources exist. ETF labels represent source instruments, not holdings. Global factor and sector scores remain independent of USA scores.')
