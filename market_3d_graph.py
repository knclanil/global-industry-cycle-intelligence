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
*{box-sizing:border-box}html,body{margin:0;background:#07090d;color:#f1f3f6;font-family:system-ui,Arial,sans-serif}#app{height:100vh;min-height:650px;position:relative;overflow:hidden;background:#07090d;border:1px solid #272c36;border-radius:10px}#bar{position:absolute;z-index:5;top:12px;left:12px;right:12px;display:flex;flex-wrap:wrap;gap:7px;align-items:center;padding:9px;background:#121722eb;border:1px solid #303744;border-radius:9px}button,input,select{border:1px solid #444d5b;background:#1b2230;color:#f5f6f8;border-radius:6px;padding:8px 10px;font:13px system-ui}button{cursor:pointer}button:hover{background:#303b50}input{flex:1;min-width:160px;max-width:320px}#stage{position:absolute;inset:0;overflow:auto;scrollbar-color:#566070 #10151d;touch-action:pan-x pan-y}svg{display:block;overflow:visible}path.edge{fill:none;stroke:#7b8494;stroke-opacity:.52;stroke-width:1.4}circle{fill:#aeb4be;stroke:#eef2f6;stroke-width:1.1;cursor:pointer}circle:hover{fill:white;stroke-width:2.4}.label{font:13px system-ui,Arial,sans-serif;fill:#e7ecf4;paint-order:stroke;stroke:#07090d;stroke-width:3px;stroke-linejoin:round;pointer-events:none}.label.strong{font-weight:700;font-size:15px}.node{cursor:pointer}.node:focus circle{stroke:#fff;stroke-width:3}#tip{display:none;position:fixed;z-index:10;pointer-events:none;background:#222a37;border:1px solid #697485;border-radius:9px;padding:11px 14px;font-size:13px;max-width:350px;box-shadow:0 8px 30px #000a}#tip strong{display:block;font-size:15px;margin-bottom:5px}#status{position:absolute;bottom:8px;left:14px;z-index:4;color:#a8b0bd;background:#0b0e15dd;padding:5px 9px;border-radius:5px;font-size:12px;pointer-events:none}@media(max-width:650px){#bar{gap:5px;padding:7px}button,input,select{font-size:12px;padding:7px}#status{font-size:10px}}
</style></head><body><div id="app"><div id="stage"><svg id="svg" aria-label="Expandable performance hierarchy"><g id="edges"></g><g id="nodes"></g></svg></div><div id="bar"><input id="search" placeholder="Search countries, sectors, factors, ETFs" aria-label="Find node"><select id="orientation" aria-label="Graph direction"><option value="auto">Auto direction</option><option value="horizontal">Left → right</option><option value="vertical">Top → bottom</option></select><button id="fit">Fit view</button><button id="open">Expand all</button><button id="close">Collapse</button><button id="plus">＋</button><button id="minus">−</button></div><div id="tip"></div><div id="status"></div></div><script>
(()=>{'use strict';const data=__PAYLOAD__,items=new Map(data.nodes.map(n=>[n.id,n])),children=new Map(),parent=new Map();for(const n of data.nodes){if(n.parent){if(!children.has(n.parent))children.set(n.parent,[]);children.get(n.parent).push(n.id);parent.set(n.id,n.parent)}}const app=document.getElementById('app'),stage=document.getElementById('stage'),svg=document.getElementById('svg'),edges=document.getElementById('edges'),nodes=document.getElementById('nodes'),tip=document.getElementById('tip'),status=document.getElementById('status'),NS='http://www.w3.org/2000/svg';let expanded=new Set(['global']),zoom=1,orientation='auto',layoutCache=null,focusId=null;const $=id=>document.getElementById(id);function el(tag,attrs){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs||{}))e.setAttribute(k,v);return e}function visible(){const out=[];function walk(id,d){out.push({id,d});if(expanded.has(id))for(const k of children.get(id)||[])walk(k,d+1)}walk('global',0);return out}function direction(){return orientation==='auto'?(app.clientWidth<700?'vertical':'horizontal'):orientation}function diameter(n,count){const base=Math.max(.85,Math.min(1.2,Math.sqrt(app.clientWidth/1200)));const perf=n.score==null?22:18+Math.sqrt(Math.max(0,Math.min(100,n.score))/100)*30;return Math.max(16,Math.min(58,perf*base))}function measure(){const rows=visible(),dir=direction(),count=rows.length,maxD=Math.max(...rows.map(r=>r.d));const labelWidth=Math.min(310,Math.max(190,app.clientWidth/Math.max(2,maxD+1)-15));const stepX=Math.max(235,labelWidth+48),stepY=Math.max(57,Math.min(79,app.clientHeight/Math.max(6,Math.min(count,12))));let cursor=0;const coords=new Map();const walk=(id,depth)=>{const kids=expanded.has(id)?children.get(id)||[]:[];if(!kids.length){coords.set(id,{d:depth,t:cursor++*stepY});return}for(const k of kids)walk(k,depth+1);const vals=kids.map(k=>coords.get(k).t);coords.set(id,{d:depth,t:(vals[0]+vals[vals.length-1])/2})};walk('global',0);const pad=75,top=115;const width=dir==='horizontal'?(maxD+1)*stepX+labelWidth+pad*2:Math.max(app.clientWidth,(cursor+1)*stepX+pad*2),height=dir==='horizontal'?Math.max(app.clientHeight,(cursor+1)*stepY+top+pad):(maxD+1)*stepY*2+top+pad*2;const points=new Map();for(const [id,p] of coords)points.set(id,dir==='horizontal'?{x:pad+p.d*stepX,y:top+p.t}:{x:pad+p.t/stepY*stepX,y:top+p.d*stepY*2});return {rows,points,width,height,dir,count}}function draw(mode='keep'){const old=layoutCache,oldCenter=old?{x:stage.scrollLeft+stage.clientWidth/2,y:stage.scrollTop+stage.clientHeight/2}:null;layoutCache=measure();const L=layoutCache;svg.setAttribute('width',Math.ceil(L.width*zoom));svg.setAttribute('height',Math.ceil(L.height*zoom));svg.setAttribute('viewBox',`0 0 ${L.width} ${L.height}`);edges.replaceChildren();nodes.replaceChildren();for(const r of L.rows){const n=items.get(r.id),p=L.points.get(r.id);if(n.parent&&L.points.has(n.parent)){const q=L.points.get(n.parent),horizontal=L.dir==='horizontal';const path=horizontal?`M ${q.x} ${q.y} C ${(q.x+p.x)/2} ${q.y}, ${(q.x+p.x)/2} ${p.y}, ${p.x} ${p.y}`:`M ${q.x} ${q.y} C ${q.x} ${(q.y+p.y)/2}, ${p.x} ${(q.y+p.y)/2}, ${p.x} ${p.y}`;edges.append(el('path',{d:path,class:'edge'}))}}for(const r of L.rows){const n=items.get(r.id),p=L.points.get(r.id),rad=diameter(n,L.count)/2,g=el('g',{class:'node',transform:`translate(${p.x} ${p.y})`,tabindex:'0',role:'button','aria-label':n.label});g.append(el('circle',{r:rad}));const label=el('text',{class:'label'+(['root','group','asset'].includes(n.kind)?' strong':''),x:L.dir==='horizontal'?rad+10:0,y:L.dir==='horizontal'?5:rad+19,'text-anchor':L.dir==='horizontal'?'start':'middle'});label.textContent=n.label;g.append(label);const title=el('title');title.textContent=n.label;g.append(title);g.addEventListener('pointerenter',e=>tooltip(e,n));g.addEventListener('pointermove',e=>tooltip(e,n));g.addEventListener('pointerleave',()=>tip.style.display='none');const toggle=()=>{if(!children.has(n.id))return;expanded.has(n.id)?expanded.delete(n.id):expanded.add(n.id);focusId=n.id;draw('focus')};g.addEventListener('click',toggle);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle()}});nodes.append(g)}status.textContent=`${L.rows.length} visible / ${data.nodes.length} total · ${L.dir==='horizontal'?'Horizontal':'Vertical'} · Scroll to explore · Hover for performance · Click to expand`;requestAnimationFrame(()=>{if(mode==='fit'){fit()}else if(mode==='focus'&&focusId){center(focusId)}else if(oldCenter){stage.scrollLeft=Math.max(0,oldCenter.x*zoom/(old?old.width*zoom||1:1)-stage.clientWidth/2);stage.scrollTop=Math.max(0,oldCenter.y*zoom/(old?old.height*zoom||1:1)-stage.clientHeight/2)}})}function tooltip(e,n){tip.style.display='block';tip.replaceChildren();const t=document.createElement('strong');t.textContent=n.label;tip.append(t);const d=document.createElement('div');d.textContent=`Performance: ${n.score==null?'unavailable':Number(n.score).toFixed(1)+'/100'} · Circle diameter: ${Math.round(diameter(n,layoutCache.count))} graph units`+(n.ticker?' · ETF: '+n.ticker:'');tip.append(d);tip.style.left=Math.max(8,Math.min(e.clientX+14,innerWidth-365))+'px';tip.style.top=Math.max(8,Math.min(e.clientY+12,innerHeight-90))+'px'}function center(id){const p=layoutCache.points.get(id);if(!p)return;stage.scrollTo({left:Math.max(0,p.x*zoom-stage.clientWidth/2),top:Math.max(0,p.y*zoom-stage.clientHeight/2),behavior:'smooth'})}function fit(){const L=layoutCache;if(!L)return;zoom=Math.max(.22,Math.min(1.35,Math.min((stage.clientWidth-25)/L.width,(stage.clientHeight-25)/L.height)));svg.setAttribute('width',Math.ceil(L.width*zoom));svg.setAttribute('height',Math.ceil(L.height*zoom));stage.scrollTo({left:0,top:0})}function readable(){zoom=1;draw('focus')}function setZoom(v){const cx=(stage.scrollLeft+stage.clientWidth/2)/zoom,cy=(stage.scrollTop+stage.clientHeight/2)/zoom;zoom=Math.max(.2,Math.min(3,v));svg.setAttribute('width',Math.ceil(layoutCache.width*zoom));svg.setAttribute('height',Math.ceil(layoutCache.height*zoom));stage.scrollLeft=cx*zoom-stage.clientWidth/2;stage.scrollTop=cy*zoom-stage.clientHeight/2}$('fit').onclick=fit;$('open').onclick=()=>{expanded=new Set(data.nodes.map(n=>n.id));focusId='global';readable()};$('close').onclick=()=>{expanded=new Set(['global']);zoom=1;draw('fit')};$('plus').onclick=()=>setZoom(zoom*1.2);$('minus').onclick=()=>setZoom(zoom/1.2);$('orientation').onchange=e=>{orientation=e.target.value;zoom=1;draw('fit')};$('search').oninput=e=>{const q=e.target.value.toLowerCase().trim();if(!q)return;const n=data.nodes.find(n=>n.label.toLowerCase().includes(q)||(n.ticker||'').toLowerCase().includes(q));if(!n)return;for(let p=n.parent;p;p=parent.get(p))expanded.add(p);zoom=1;draw('focus');center(n.id)};let resizeTimer;new ResizeObserver(()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>draw('keep'),170)}).observe(app);draw('fit')})();
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
