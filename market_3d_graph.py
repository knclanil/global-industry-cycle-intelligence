"""Responsive 2D market knowledge graph; excludes companies and constituent holdings."""
import json
from datetime import date, timedelta
import streamlit as st
import streamlit.components.v1 as components

GROUPS = {
    'Countries': ['Countries'],
    'Asset Classes': ['Global Assets', 'USA Assets', 'India Assets'],
    'Factors': ['Global Factors', 'USA Factors', 'India Factors'],
    'Sectors': ['Global Sectors', 'USA Sectors', 'India Sectors'],
}
KIND_COLORS = {'Countries':'#36c5a0','Asset Classes':'#e3ac58','Factors':'#a99af7','Sectors':'#62a9e8'}
STATUS_COLORS = {'Leading':'#39cf91','Improving':'#65a9ff','Weakening':'#eab45e','Lagging':'#ed7280','Unavailable':'#8794a6'}

def graph_payload(layers, limit=8):
    """Only link observed market instruments to their own source group; never infer cross-market relationships."""
    nodes, links = [], []
    for kind, sources in GROUPS.items():
        available = [(s, layers[s]) for s in sources if s in layers and not layers[s].empty]
        if not available:
            continue
        nodes.append({'id':'group:'+kind,'label':kind,'kind':'group','category':kind,'color':KIND_COLORS[kind], 'size':9})
        for source, frame in available:
            parent='group:'+kind
            if len(available)>1:
                parent='source:'+source
                nodes.append({'id':parent,'label':source,'kind':'source','category':kind,'color':KIND_COLORS[kind],'size':5})
                links.append({'source':'group:'+kind,'target':parent,'type':'contains'})
            for _, row in frame.nlargest(limit,'Network Score').iterrows():
                ticker=str(row.get('ETF','')).strip()
                label=str(row.get('Sector',ticker)).strip() or ticker
                quadrant=str(row.get('Quadrant','Unavailable'))
                score=round(float(row['Network Score']),1)
                ident=f'item:{source}:{ticker}'
                nodes.append({'id':ident,'label':label,'ticker':ticker,'source':source,'kind':'market',
                              'category':kind,'status':quadrant,'score':score,
                              'color':KIND_COLORS[kind], 'statusColor':STATUS_COLORS.get(quadrant,STATUS_COLORS['Unavailable']),
                              'size':3.0+score/45})
                links.append({'source':parent,'target':ident,'type':'observed in'})
    return {'nodes':nodes,'links':links}

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}html,body{margin:0;background:#06090e;color:#e8eef7;font:14px system-ui,Segoe UI,sans-serif}#shell{height:720px;min-height:520px;position:relative;overflow:hidden;background:#06090e;border:1px solid #263141;border-radius:12px}#canvas{width:100%;height:100%;display:block;touch-action:none;cursor:grab}#canvas.dragging{cursor:grabbing}#tools{position:absolute;top:12px;left:12px;right:12px;display:flex;gap:7px;flex-wrap:wrap;z-index:2;pointer-events:none}button,input{pointer-events:auto;background:#111b28;border:1px solid #334357;color:#e6edf6;border-radius:7px;padding:9px 11px;font:inherit}button{cursor:pointer}button:hover{background:#20334a}input{width:min(235px,45vw)}#details{position:absolute;right:12px;top:64px;width:260px;max-width:38%;max-height:62%;overflow:auto;padding:15px;background:#101923f2;border:1px solid #314154;border-radius:10px;z-index:2;box-shadow:0 12px 35px #0007}#details h3{margin:6px 0;font-size:18px;overflow-wrap:anywhere}#details p{color:#b2c0d0;line-height:1.5}#details small{color:#8ca1b6}#legend{position:absolute;bottom:12px;left:12px;right:12px;max-width:max-content;background:#101923ec;border:1px solid #304052;border-radius:7px;padding:8px 10px;font-size:12px;z-index:2;line-height:2}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 4px 0 10px}#notice{position:absolute;bottom:60px;left:16px;color:#91a2b5;font-size:12px;pointer-events:none}svg text{font-family:system-ui,Segoe UI,sans-serif;paint-order:stroke;stroke:#06090e;stroke-width:3px;stroke-linejoin:round;fill:#e2eaf4;font-size:13px;pointer-events:none}svg .edge{stroke:#506070;stroke-width:1;stroke-opacity:.36;pointer-events:none}svg .item{cursor:pointer}svg .item:focus{outline:none}svg .item:focus circle{stroke:white;stroke-width:3}svg .node{stroke:#09121c;stroke-width:2}svg .status{stroke:#06090e;stroke-width:1}#close{float:right;padding:1px 7px}@media(max-width:700px){#shell{height:640px}#details{top:auto;bottom:70px;right:8px;max-width:none;width:min(300px,75%);max-height:36%;padding:10px}#legend{font-size:10px;max-width:96%}#notice{display:none}button,input{padding:7px;font-size:12px}}
</style></head><body><div id="shell"><div id="tools"><input id="search" placeholder="Search country, factor, ETF…" aria-label="Search nodes"><button id="fit">Fit</button><button id="expand">Expand all</button><button id="collapse">Collapse</button><button id="reset">Reset</button><button id="zoomIn">＋</button><button id="zoomOut">−</button></div><svg id="canvas" role="img" aria-label="Interactive market relationship knowledge graph" tabindex="0"><g id="viewport"><g id="edges"></g><g id="nodes"></g></g></svg><aside id="details"><button id="close" aria-label="Close details">×</button><small>MARKET KNOWLEDGE GRAPH</small><h3 id="title">Explore market relationships</h3><p id="info">Select a node to highlight its verified connections. Click a category to expand or collapse it.</p></aside><div id="notice">Drag to pan · Scroll to zoom · Select a node to focus</div><div id="legend">NODE TYPE <span class="dot" style="background:#36c5a0"></span>Countries <span class="dot" style="background:#e3ac58"></span>Assets <span class="dot" style="background:#a99af7"></span>Factors <span class="dot" style="background:#62a9e8"></span>Sectors &nbsp; | &nbsp; STATUS <span class="dot" style="background:#39cf91"></span>Leading <span class="dot" style="background:#65a9ff"></span>Improving <span class="dot" style="background:#eab45e"></span>Weakening <span class="dot" style="background:#ed7280"></span>Lagging</div></div><script>
(()=>{'use strict';const data=__PAYLOAD__,svg=document.getElementById('canvas'),vp=document.getElementById('viewport'),edges=document.getElementById('edges'),nodes=document.getElementById('nodes');const byId=new Map(data.nodes.map(n=>[n.id,n]));const children=new Map(),parents=new Map();for(const l of data.links){if(!children.has(l.source))children.set(l.source,[]);children.get(l.source).push(l.target);parents.set(l.target,l.source)}const groups=data.nodes.filter(n=>n.kind==='group');const expanded=new Set(groups.map(n=>n.id));let selected=null,scale=1,tx=0,ty=0,drag=false,moved=false,lastX=0,lastY=0;const NS='http://www.w3.org/2000/svg';const elem=(tag,attrs)=>{let el=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs||{}))el.setAttribute(k,v);return el};function visible(){const ids=new Set(groups.map(n=>n.id));for(let i=0;i<4;i++)for(const l of data.links)if(ids.has(l.source)&&expanded.has(l.source))ids.add(l.target);return ids}function layout(ids){
  const w=svg.clientWidth||1000,h=svg.clientHeight||720;
  const positions=new Map();
  // Four balanced category regions; each source and market leaf gets its own orbit.
  const centers=[[w*.26,h*.32],[w*.69,h*.32],[w*.26,h*.69],[w*.69,h*.69]];
  const cats=groups.filter(n=>ids.has(n.id));
  cats.forEach((g,i)=>{
    const [gx,gy]=centers[i%4];positions.set(g.id,[gx,gy]);
    const kids=(children.get(g.id)||[]).filter(id=>ids.has(id));
    const angle0=-Math.PI/2;
    kids.forEach((id,j)=>{
      const a=angle0+2*Math.PI*j/Math.max(kids.length,1);
      const r=kids.length>5?Math.min(w*.16,145):Math.min(w*.13,110);
      const sx=gx+Math.cos(a)*r,sy=gy+Math.sin(a)*r;
      positions.set(id,[sx,sy]);
      const grand=(children.get(id)||[]).filter(x=>ids.has(x));
      grand.forEach((cid,k)=>{
        const aa=a+(k-(grand.length-1)/2)*Math.min(.32,2.8/Math.max(grand.length,1));
        const rr=120+Math.floor(k/8)*48;
        positions.set(cid,[sx+Math.cos(aa)*rr,sy+Math.sin(aa)*rr]);
      });
    });
  });
  // Repel overlapping label boxes, not merely overlapping circles.
  const entries=[...positions.entries()];
  const sizes=new Map(entries.map(([id])=>{const n=byId.get(id);return [id,[Math.min(220,32+(n.label||'').length*6.7),n.kind==='group'?39:27]]}));
  for(let pass=0;pass<125;pass++){
    for(let i=0;i<entries.length;i++)for(let j=i+1;j<entries.length;j++){
      const [idA,pa]=entries[i],[idB,pb]=entries[j];
      const [wa,ha]=sizes.get(idA),[wb,hb]=sizes.get(idB);
      const dx=pb[0]-pa[0],dy=pb[1]-pa[1];
      const ox=(wa+wb)*.5+14-Math.abs(dx),oy=(ha+hb)*.5+9-Math.abs(dy);
      if(ox>0&&oy>0){
        const signX=dx===0?(i%2?1:-1):Math.sign(dx),signY=dy===0?(j%2?1:-1):Math.sign(dy);
        const weightA=byId.get(idA).kind==='group'?.10:.48;
        const weightB=byId.get(idB).kind==='group'?.10:.48;
        if(ox<oy*2){pa[0]-=signX*ox*weightA;pb[0]+=signX*ox*weightB}
        else{pa[1]-=signY*oy*weightA;pb[1]+=signY*oy*weightB}
      }
    }
  }
  return positions;
}function transform(){vp.setAttribute('transform',`translate(${tx} ${ty}) scale(${scale})`)}function focus(id){selected=id;const n=byId.get(id);document.getElementById('title').textContent=n.label;document.getElementById('info').textContent=[n.category,n.status?`Status: ${n.status}`:null,Number.isFinite(n.score)?`Leadership score: ${n.score}`:null,n.source?`Source: ${n.source}`:null,n.ticker?`Ticker: ${n.ticker}`:null,'Connections show source-category membership, not capital flows or holdings.'].filter(Boolean).join(' · ');draw()}function draw(){edges.replaceChildren();nodes.replaceChildren();const ids=visible(),pos=layout(ids),neighbors=new Set([selected]);if(selected){for(const l of data.links)if(l.source===selected)neighbors.add(l.target);else if(l.target===selected)neighbors.add(l.source)}for(const l of data.links){if(!ids.has(l.source)||!ids.has(l.target)||!pos.has(l.source)||!pos.has(l.target))continue;const [x1,y1]=pos.get(l.source),[x2,y2]=pos.get(l.target),line=elem('line',{x1,y1,x2,y2,class:'edge'});if(selected){line.style.strokeOpacity=(l.source===selected||l.target===selected)?'.95':'.08';line.style.strokeWidth=(l.source===selected||l.target===selected)?'2':'1'}edges.append(line)}for(const n of data.nodes){if(!ids.has(n.id)||!pos.has(n.id))continue;const [x,y]=pos.get(n.id),group=elem('g',{class:'item',tabindex:'0',role:'button','aria-label':n.label,transform:`translate(${x} ${y})`}),r=n.kind==='group'?15:n.kind==='source'?10:6;group.style.opacity=selected&&!neighbors.has(n.id)?'.24':'1';group.append(elem('circle',{r:r+4,fill:'none',stroke:n.statusColor||n.color,'stroke-width':n.kind==='market'?2:1,'stroke-opacity':'.85'}));group.append(elem('circle',{r,class:'node',fill:n.color}));const showLabel=true; if(showLabel){const label=elem('text',{x:r+9,y:4});label.textContent=n.label;group.append(label)}group.addEventListener('click',e=>{e.stopPropagation();if(moved)return;if(n.kind==='group'||n.kind==='source'){expanded.has(n.id)?expanded.delete(n.id):expanded.add(n.id)}focus(n.id)});group.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();group.dispatchEvent(new Event('click'))}});const title=elem('title');title.textContent=n.label+(n.status?' — '+n.status:'');group.append(title);nodes.append(group)}}function fit(){const ids=visible(),p=layout(ids),coords=[...p.values()];if(!coords.length)return;const xs=coords.map(x=>x[0]),ys=coords.map(x=>x[1]);const minx=Math.min(...xs)-70,maxx=Math.max(...xs)+260,miny=Math.min(...ys)-85,maxy=Math.max(...ys)+90;const w=svg.clientWidth,h=svg.clientHeight;scale=Math.min(1.4,Math.max(.35,Math.min((w-35)/(maxx-minx),(h-155)/(maxy-miny))));tx=w/2-scale*(minx+maxx)/2;ty=h/2-scale*(miny+maxy)/2;transform()}function zoom(mult){scale=Math.min(4,Math.max(.3,scale*mult));transform()}svg.addEventListener('pointerdown',e=>{if(e.target.closest('.item'))return;drag=true;moved=false;lastX=e.clientX;lastY=e.clientY;svg.setPointerCapture(e.pointerId);svg.classList.add('dragging')});svg.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-lastX,dy=e.clientY-lastY;if(Math.abs(dx)+Math.abs(dy)>2)moved=true;tx+=dx;ty+=dy;lastX=e.clientX;lastY=e.clientY;transform()});svg.addEventListener('pointerup',()=>{drag=false;svg.classList.remove('dragging');setTimeout(()=>moved=false,50)});svg.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY<0?1.12:1/1.12)},{passive:false});document.getElementById('zoomIn').onclick=()=>zoom(1.25);document.getElementById('zoomOut').onclick=()=>zoom(.8);document.getElementById('fit').onclick=fit;document.getElementById('expand').onclick=()=>{data.nodes.filter(n=>n.kind==='group'||n.kind==='source').forEach(n=>expanded.add(n.id));draw();fit()};document.getElementById('collapse').onclick=()=>{expanded.clear();selected=null;draw();fit()};document.getElementById('reset').onclick=()=>{selected=null;expanded.clear();groups.forEach(n=>expanded.add(n.id));draw();fit()};document.getElementById('close').onclick=()=>{selected=null;document.getElementById('title').textContent='Explore market relationships';document.getElementById('info').textContent='Select a node to highlight its verified connections.';draw()};document.getElementById('search').addEventListener('input',e=>{const q=e.target.value.toLowerCase().trim();if(!q){selected=null;draw();return}const match=data.nodes.find(n=>n.label.toLowerCase().includes(q)||(n.ticker||'').toLowerCase().includes(q));if(match){let p=parents.get(match.id);while(p){expanded.add(p);p=parents.get(p)}focus(match.id)}});let resizeTimer;new ResizeObserver(()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{draw();fit()},100)}).observe(svg);draw();fit();})();
</script></body></html>'''

def render():
    from capital_network import fetch_layer
    import country_market_data
    st.title('Global Market Intelligence · Knowledge Graph')
    st.caption('Auto-scaling 2D market relationships · no company nodes or constituent holdings · peer-relative scores, not capital flows')
    a,b,c=st.columns([2,2,1])
    with a: groups=st.multiselect('Node categories',list(GROUPS),default=list(GROUPS))
    with b: lookback=st.select_slider('Relative strength period',options=list(country_market_data.LOOKBACKS),value='3M')
    with c: top=st.selectbox('Markets per source',[5,8,12,20],index=1)
    period=st.date_input('Observation dates',value=(date.today()-timedelta(days=365),date.today()),max_value=date.today())
    if not isinstance(period,(tuple,list)) or len(period)!=2 or period[0]>=period[1]:
        st.info('Select a valid start and end date.');return
    layers,errors={},{}
    with st.spinner('Loading verified market observations…'):
        for group in groups:
            for source in GROUPS[group]:
                try:layers[source],_=fetch_layer(source,period[0],period[1],lookback)
                except Exception as exc:errors[source]=str(exc)
    payload=graph_payload(layers,top)
    if not payload['nodes']:
        st.warning('No verified market data is available for the selected filters.');return
    st.caption(f"{len(payload['nodes'])} nodes · {len(payload['links'])} verified category relationships · click categories to expand/collapse")
    components.html(HTML.replace('__PAYLOAD__',json.dumps(payload).replace('</','<\\/')),height=750,scrolling=False)
    if errors:
        with st.expander(f'Unavailable market sources ({len(errors)})'):
            for source,error in errors.items():st.caption(f'{source}: {error}')
    st.caption('Connections indicate verified market-series membership in a source category. ETF price proxies do not establish fund holdings or company relationships. Rendered with native SVG; no external JavaScript libraries or 3D renderer.')
