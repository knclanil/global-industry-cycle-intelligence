"""Responsive orbital 2D market knowledge graph, no constituent companies."""
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
*{box-sizing:border-box}html,body{margin:0;background:#07090d;color:#f1f3f6;font-family:system-ui,Arial,sans-serif}#app{height:100vh;min-height:650px;position:relative;overflow:hidden;background:#07090d;border:1px solid #272c36;border-radius:10px}#bar{position:absolute;z-index:5;top:12px;left:12px;right:12px;display:flex;flex-wrap:wrap;gap:7px;align-items:center;padding:9px;background:#121722eb;border:1px solid #303744;border-radius:9px}button,input,select{border:1px solid #444d5b;background:#1b2230;color:#f5f6f8;border-radius:6px;padding:8px 10px;font:13px system-ui}button{cursor:pointer}button:hover{background:#303b50}input{flex:1;min-width:160px;max-width:320px}#stage{position:absolute;inset:0;overflow:auto;scrollbar-color:#566070 #10151d;touch-action:pan-x pan-y}svg{display:block;overflow:visible}path.edge{fill:none;stroke:#7b8494;stroke-opacity:.52;stroke-width:1.4}circle{fill:#aeb4be;stroke:#eef2f6;stroke-width:1.1;cursor:pointer}circle:hover{fill:white;stroke-width:2.4}.score-inside{fill:#111722;font-family:system-ui,Arial,sans-serif;font-weight:800;pointer-events:none;dominant-baseline:central;text-anchor:middle;font-variant-numeric:tabular-nums}.label{font:13px system-ui,Arial,sans-serif;fill:#e7ecf4;paint-order:stroke;stroke:#07090d;stroke-width:3px;stroke-linejoin:round;pointer-events:none}.label.strong{font-weight:700;font-size:15px}.node{cursor:pointer}.node:focus circle{stroke:#fff;stroke-width:3}#tip{display:none;position:fixed;z-index:10;pointer-events:none;background:#222a37;border:1px solid #697485;border-radius:9px;padding:11px 14px;font-size:13px;max-width:350px;box-shadow:0 8px 30px #000a}#tip strong{display:block;font-size:15px;margin-bottom:5px}#status{position:absolute;bottom:8px;left:14px;z-index:4;color:#a8b0bd;background:#0b0e15dd;padding:5px 9px;border-radius:5px;font-size:12px;pointer-events:none}@media(max-width:650px){#bar{gap:5px;padding:7px}button,input,select{font-size:12px;padding:7px}#status{font-size:10px}}
</style></head><body><div id="app"><div id="stage"><svg id="svg" aria-label="Expandable performance hierarchy"><g id="edges"></g><g id="nodes"></g></svg></div><div id="bar"><input id="search" placeholder="Search countries, sectors, factors, ETFs" aria-label="Find node"><button id="fit">Fit view</button><button id="open">Expand all</button><button id="close">Collapse</button><button id="plus">＋</button><button id="minus">−</button></div><div id="tip"></div><div id="status"></div></div><script>
(()=>{'use strict';
const data=__PAYLOAD__, items=new Map(data.nodes.map(n=>[n.id,n])),children=new Map(),parent=new Map();
for(const n of data.nodes){if(n.parent){if(!children.has(n.parent))children.set(n.parent,[]);children.get(n.parent).push(n.id);parent.set(n.id,n.parent)}}
const stage=document.getElementById('stage'),svg=document.getElementById('svg'),edges=document.getElementById('edges'),nodes=document.getElementById('nodes'),tip=document.getElementById('tip'),status=document.getElementById('status'),NS='http://www.w3.org/2000/svg';
let expanded=new Set(['global']),zoom=1,layout=null,focusId=null,drag=null;const $=id=>document.getElementById(id);
function el(tag,attrs={}){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e}
function visible(){const out=[];function walk(id,d){out.push({id,d});if(expanded.has(id))for(const c of children.get(id)||[])walk(c,d+1)}walk('global',0);return out}
function score(n){return Number.isFinite(Number(n.score))&&n.score!==null?Math.max(0,Math.min(100,Number(n.score))):null}
function diameter(n){const sc=score(n),responsive=Math.max(.85,Math.min(1.15,Math.sqrt(stage.clientWidth/1150)));return Math.max(22,Math.min(70,(sc===null?31:23+Math.sqrt(sc/100)*37)*responsive))}
function measure(){const rows=visible(),byId=new Map(rows.map(r=>[r.id,r])),maxDepth=Math.max(...rows.map(r=>r.d)),count=rows.length;
// A full circle is allocated to the root. Descendants occupy proportional angular sectors of their ancestors.
const weight=new Map();function mass(id){const kids=expanded.has(id)?children.get(id)||[]:[];let w=kids.length?kids.reduce((s,k)=>s+mass(k),0):1;weight.set(id,w);return w}mass('global');
const levels=new Map();for(const r of rows){levels.set(r.d,(levels.get(r.d)||0)+1)}
// Enough circumference for labels and circles. Expanding all increases canvas size, not shrinks text.
const ring=[0];for(let d=1;d<=maxDepth;d++){const n=levels.get(d)||1;const needed=(n*115)/(2*Math.PI);ring[d]=Math.max((ring[d-1]||0)+175,needed+120,d*185)}
const points=new Map(),polar=new Map();const root=items.get('global');polar.set('global',{angle:0,r:0});
function place(id,start,end,depth){const kids=expanded.has(id)?children.get(id)||[]:[];if(!kids.length)return;
// Highest score comes first and is closer to its parent within the same orbital band.
const sorted=[...kids].sort((a,b)=>(score(items.get(b))??-1)-(score(items.get(a))??-1));const total=sorted.reduce((v,k)=>v+weight.get(k),0);let angle=start;
for(const k of sorted){const portion=(end-start)*weight.get(k)/total,mid=angle+portion/2,sc=score(items.get(k));const offset=sc===null?48:(100-sc)*.9;const r=ring[depth+1]+offset;polar.set(k,{angle:mid,r});place(k,angle,angle+portion,depth+1);angle+=portion}}
place('global',-.5*Math.PI,1.5*Math.PI,0);
const maxR=Math.max(450,...[...polar.values()].map(v=>v.r))+270;const width=Math.max(stage.clientWidth,maxR*2),height=Math.max(stage.clientHeight,maxR*2),cx=width/2,cy=height/2;
for(const [id,v] of polar)points.set(id,{x:cx+Math.cos(v.angle)*v.r,y:cy+Math.sin(v.angle)*v.r});return {rows,points,width,height,count,maxDepth,cx,cy}}
function bounds(){
 // Fit to actual visible geometry, including the permanent labels, rather than
 // the much larger theoretical square occupied by the orbital layout.
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
 for(const row of layout.rows){const n=items.get(row.id),p=layout.points.get(row.id),r=diameter(n)/2;
 const labelWidth=Math.min(520,Math.max(42,n.label.length*7.8));
 minX=Math.min(minX,p.x-r-12);maxX=Math.max(maxX,p.x+r+12+labelWidth);
 minY=Math.min(minY,p.y-r-15);maxY=Math.max(maxY,p.y+r+15);
 }
 const pad=35;return {x:minX-pad,y:minY-pad,w:Math.max(1,maxX-minX+pad*2),h:Math.max(1,maxY-minY+pad*2)};
}
function updateSvg(){const b=layout.fitBounds||{x:0,y:0,w:layout.width,h:layout.height};
 svg.setAttribute('width',Math.ceil(b.w*zoom));svg.setAttribute('height',Math.ceil(b.h*zoom));
 svg.setAttribute('viewBox',`${b.x} ${b.y} ${b.w} ${b.h}`);
}
function stagePoint(p){const b=layout.fitBounds||{x:0,y:0};return {x:(p.x-b.x)*zoom,y:(p.y-b.y)*zoom}}

function center(id,smooth=false){const p=layout.points.get(id);if(!p)return;const v=stagePoint(p);stage.scrollTo({left:v.x-stage.clientWidth/2,top:v.y-stage.clientHeight/2,behavior:smooth?'smooth':'instant'})}
function fit(){if(!layout)return;
 layout.fitBounds=bounds();const b=layout.fitBounds;
 // Use the real occupied rectangle; maximize visible area without clipping.
 zoom=Math.max(.08,Math.min(4,Math.min((stage.clientWidth-24)/b.w,(stage.clientHeight-100)/b.h)));
 updateSvg();stage.scrollLeft=Math.max(0,(svg.clientWidth-stage.clientWidth)/2);
 stage.scrollTop=Math.max(0,(svg.clientHeight-stage.clientHeight)/2);
}
function draw(mode='keep'){const previous=layout,oldZoom=zoom,oldCenter=previous?{x:(stage.scrollLeft+stage.clientWidth/2)/oldZoom+(previous.fitBounds?.x||0),y:(stage.scrollTop+stage.clientHeight/2)/oldZoom+(previous.fitBounds?.y||0)}:null;layout=measure();layout.fitBounds=bounds();updateSvg();edges.replaceChildren();nodes.replaceChildren();
for(const r of layout.rows){const n=items.get(r.id),p=layout.points.get(r.id);if(n.parent&&layout.points.has(n.parent)){const q=layout.points.get(n.parent);edges.append(el('path',{d:`M ${q.x} ${q.y} L ${p.x} ${p.y}`,class:'edge'}))}}
for(const r of layout.rows){const n=items.get(r.id),p=layout.points.get(r.id),rad=diameter(n)/2,g=el('g',{class:'node',transform:`translate(${p.x} ${p.y})`,tabindex:'0',role:'button','aria-label':n.label});g.append(el('circle',{r:rad}));const sc=score(n);if(sc!==null){const t=el('text',{class:'score-inside','font-size':Math.max(10,Math.min(18,rad*.84)),y:0});t.textContent=String(Math.round(sc));g.append(t)}const text=el('text',{class:'label'+(['root','group','asset'].includes(n.kind)?' strong':''),x:rad+9,y:5});text.textContent=n.label;g.append(text);const title=el('title');title.textContent=n.label;g.append(title);g.addEventListener('pointerenter',e=>tooltip(e,n));g.addEventListener('pointermove',e=>tooltip(e,n));g.addEventListener('pointerleave',()=>tip.style.display='none');const toggle=()=>{if(!children.has(n.id))return;expanded.has(n.id)?expanded.delete(n.id):expanded.add(n.id);focusId=n.id;draw('focus')};g.addEventListener('click',toggle);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle()}});nodes.append(g)}
status.textContent=`${layout.count} / ${data.nodes.length} nodes · 2D orbital view · Higher score = closer orbit and larger circle · Drag to pan · Click to expand`;
requestAnimationFrame(()=>{if(mode==='fit')fit();else if(mode==='focus'&&focusId)center(focusId,true);else if(oldCenter){stage.scrollLeft=(oldCenter.x-(layout.fitBounds?.x||0))*zoom-stage.clientWidth/2;stage.scrollTop=(oldCenter.y-(layout.fitBounds?.y||0))*zoom-stage.clientHeight/2}else center('global')})}
function tooltip(e,n){tip.style.display='block';tip.replaceChildren();const h=document.createElement('strong');h.textContent=n.label;tip.append(h);const d=document.createElement('div');d.textContent=`Performance: ${score(n)===null?'unavailable':score(n).toFixed(1)+'/100'} · Diameter: ${Math.round(diameter(n))} units`+(n.ticker?' · ETF: '+n.ticker:'');tip.append(d);tip.style.left=Math.max(8,Math.min(e.clientX+14,innerWidth-365))+'px';tip.style.top=Math.max(8,Math.min(e.clientY+12,innerHeight-90))+'px'}
function setZoom(v){const x=(stage.scrollLeft+stage.clientWidth/2)/zoom,y=(stage.scrollTop+stage.clientHeight/2)/zoom;zoom=Math.max(.15,Math.min(3,v));updateSvg();stage.scrollLeft=x*zoom-stage.clientWidth/2;stage.scrollTop=y*zoom-stage.clientHeight/2}
$('fit').onclick=fit;$('open').onclick=()=>{expanded=new Set(data.nodes.map(n=>n.id));zoom=1;draw('fit')};$('close').onclick=()=>{expanded=new Set(['global']);zoom=1;draw('fit')};$('plus').onclick=()=>setZoom(zoom*1.2);$('minus').onclick=()=>setZoom(zoom/1.2);
$('search').oninput=e=>{const q=e.target.value.toLowerCase().trim();if(!q)return;const n=data.nodes.find(n=>n.label.toLowerCase().includes(q)||(n.ticker||'').toLowerCase().includes(q));if(!n)return;for(let p=n.parent;p;p=parent.get(p))expanded.add(p);zoom=Math.max(zoom,.75);focusId=n.id;draw('focus')};
// Drag on the background to pan; click targets retain expansion behavior.
stage.addEventListener('pointerdown',e=>{if(e.target.closest('.node'))return;drag={x:e.clientX,y:e.clientY,left:stage.scrollLeft,top:stage.scrollTop};stage.setPointerCapture(e.pointerId)});stage.addEventListener('pointermove',e=>{if(drag){stage.scrollLeft=drag.left+drag.x-e.clientX;stage.scrollTop=drag.top+drag.y-e.clientY}});stage.addEventListener('pointerup',()=>drag=null);stage.addEventListener('pointercancel',()=>drag=null);
let timer;new ResizeObserver(()=>{clearTimeout(timer);timer=setTimeout(()=>draw('fit'),180)}).observe(stage);draw('fit');
})();
</script></body></html>'''
def render():
    from capital_network import fetch_layer
    import country_market_data
    st.title('Global Market Intelligence · Knowledge Graph')
    st.caption('Global → Countries → Assets → Equity / Bonds / Cash; plus independent Global Sectors and Global Factors. Circle size and in-circle score indicate relative performance (0–100); no companies or holdings.')
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
    st.caption(f"{len(payload['nodes'])} available graph nodes · Click to expand branches · Labels show names · Scores appear inside circles · Hover for details")
    components.html(HTML.replace('__PAYLOAD__',json.dumps(payload).replace('</','<\\/')),height=760,scrolling=False)
    if errors:
        with st.expander(f'Unavailable data sources ({len(errors)})'):
            for name,error in errors.items():st.caption(f'{name}: {error}')
    st.caption('Country branches are shown only where country-specific sources exist. ETF labels represent source instruments, not holdings. Global factor and sector scores remain independent of USA scores.')
