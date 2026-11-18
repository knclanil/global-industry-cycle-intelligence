"""Interactive 3D market knowledge graph; excludes companies and constituent holdings."""
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

HTML = r'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#05070b;color:#edf1f6;font:14px system-ui,-apple-system,Segoe UI,sans-serif}
#wrap{height:100vh;position:relative;overflow:hidden}#graph{width:100%;height:100%}
#bar{position:absolute;z-index:2;top:14px;left:16px;display:flex;gap:8px;flex-wrap:wrap;max-width:calc(100% - 330px)}
button,input{background:#111822;color:#e4edf6;border:1px solid #334052;border-radius:7px;padding:9px 12px;font:inherit}
button{cursor:pointer}button:hover{background:#223043}button.active{border-color:#75aaff;background:#1a304b}
#search{width:185px}#detail{position:absolute;right:14px;top:14px;width:285px;background:rgba(13,19,28,.94);border:1px solid #364251;border-radius:11px;padding:17px;z-index:3;line-height:1.6;box-shadow:0 14px 40px #0008}
#detail h3{margin:0 0 7px;font-size:18px;overflow-wrap:anywhere}#detail small{color:#a6b5c5}#detail .stat{font-size:24px;font-weight:700;margin:8px 0}#detail .tag{display:inline-block;border-radius:5px;padding:2px 7px;background:#263243;margin:3px 3px 3px 0}
#legend{position:absolute;bottom:14px;left:16px;z-index:2;background:#0b111ad9;border:1px solid #293645;border-radius:8px;padding:10px;color:#c5d0dc;font-size:12px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 5px 0 10px}#hint{position:absolute;bottom:60px;left:18px;color:#94a6ba;font-size:12px;pointer-events:none}
#fallback{position:absolute;inset:25% 15%;text-align:center;color:#c5d0dc;display:none}
@media(max-width:900px){#bar{max-width:calc(100% - 20px);right:10px}#detail{top:auto;bottom:65px;width:260px;max-height:45%;overflow:auto}#legend{max-width:65%;line-height:2}#hint{display:none}}
</style></head><body><div id="wrap"><div id="graph"></div>
<div id="bar"><input id="search" placeholder="Find a market node..." aria-label="Search market nodes"><button id="reset">Reset view</button><button id="expand">Expand all</button><button id="fit">Fit graph</button></div>
<aside id="detail"><small>MARKET KNOWLEDGE GRAPH</small><h3 id="name">Select a node</h3><div id="description">Click a circle to focus on its verified relationships. Drag to rotate; scroll to zoom.</div></aside>
<div id="hint">Drag to rotate · Scroll to zoom · Click to focus · Double-click a group to expand/collapse</div>
<div id="legend">NODE TYPES <span class="dot" style="background:#36c5a0"></span>Countries <span class="dot" style="background:#e3ac58"></span>Assets <span class="dot" style="background:#a99af7"></span>Factors <span class="dot" style="background:#62a9e8"></span>Sectors<br>MARKET STATUS <span class="dot" style="background:#39cf91"></span>Leading <span class="dot" style="background:#65a9ff"></span>Improving <span class="dot" style="background:#eab45e"></span>Weakening <span class="dot" style="background:#ed7280"></span>Lagging</div>
<div id="fallback">The interactive 3D renderer could not load. Check whether your browser or network blocks the external JavaScript library.</div></div>
<script>const PAYLOAD=__PAYLOAD__;</script>
<script src="https://unpkg.com/three@0.149.0/build/three.min.js"></script>
<script src="https://unpkg.com/three-spritetext@1.9.3/dist/three-spritetext.min.js"></script>
<script src="https://unpkg.com/3d-force-graph@1.73.4/dist/3d-force-graph.min.js"></script>
<script>
(function(){
if(typeof THREE==='undefined'||typeof ForceGraph3D==='undefined'||typeof SpriteText==='undefined'){document.getElementById('fallback').style.display='block';return;}
const allNodes=PAYLOAD.nodes,allLinks=PAYLOAD.links, byId=new Map(allNodes.map(n=>[n.id,n]));
const expanded=new Set(allNodes.filter(n=>n.kind==='group').map(n=>n.id));let selected=null;
const endpoint=x=>typeof x==='object'?x.id:x;
function visible(){let ids=new Set(allNodes.filter(n=>n.kind==='group').map(n=>n.id));
for(let pass=0;pass<3;pass++){for(const l of allLinks){const p=endpoint(l.source),c=endpoint(l.target);if(ids.has(p)&&expanded.has(p))ids.add(c)}}
return {nodes:allNodes.filter(n=>ids.has(n.id)).map(n=>({...n})),links:allLinks.filter(l=>ids.has(endpoint(l.source))&&ids.has(endpoint(l.target))).map(l=>({source:endpoint(l.source),target:endpoint(l.target)}))};}
const el=document.getElementById('graph');let graph;try{graph=ForceGraph3D()(el)}catch(err){document.getElementById('fallback').style.display='block';document.getElementById('fallback').textContent='3D initialization failed: '+err.message;return;}graph.backgroundColor('#05070b').showNavInfo(false)
 .nodeRelSize(3).nodeVal(n=>n.size||4).nodeColor(n=>n.color).nodeOpacity(.92)
 .linkColor(l=>selected&&(endpoint(l.source)===selected||endpoint(l.target)===selected)?'#9eafc6':'#38414d')
 .linkOpacity(.36).linkWidth(l=>selected&&(endpoint(l.source)===selected||endpoint(l.target)===selected)?1.7:.55)
 .nodeThreeObjectExtend(true).nodeThreeObject(n=>{if(n.kind==='market'&&!selected)return false;
 const s=new SpriteText(n.label);s.color=n.id===selected?'#ffffff':'#c6d2de';s.textHeight=n.kind==='group'?5.6:n.kind==='source'?3.5:2.5;s.backgroundColor='#05070bc9';s.padding=2;s.position.set(0,(n.size||4)+5,0);return s;})
 .onNodeClick(n=>{selected=n.id;document.getElementById('name').textContent=n.label;
 document.getElementById('description').innerHTML='<div class="tag">'+n.category+'</div>'+(n.status?'<div class="stat" style="color:'+n.statusColor+'">'+n.score+' / 100</div><div>Status: '+n.status+'</div>':'')+(n.source?'<div>Data source: '+n.source+'</div>':'')+(n.ticker?'<div>Market ticker: '+n.ticker+'</div>':'')+'<p style="color:#9faebd">Connections represent source membership, not fund flows or holdings.</p>';
 graph.linkColor(graph.linkColor()).nodeThreeObject(graph.nodeThreeObject());const d=1+95/Math.hypot(n.x||1,n.y||1,n.z||1);graph.cameraPosition({x:n.x*d,y:n.y*d,z:n.z*d},n,900);})
 .onNodeDblClick(n=>{if(n.kind==='group'||n.kind==='source'){expanded.has(n.id)?expanded.delete(n.id):expanded.add(n.id);refresh();}});
function refresh(){graph.graphData(visible());graph.d3Force('charge').strength(-125);graph.d3Force('link').distance(l=>byId.get(endpoint(l.source))?.kind==='group'?85:44);}
refresh();setTimeout(()=>graph.zoomToFit(650,65),1300);
document.getElementById('reset').onclick=()=>{selected=null;document.getElementById('name').textContent='Select a node';document.getElementById('description').textContent='Click a circle to focus on its verified relationships. Drag to rotate; scroll to zoom.';graph.cameraPosition({x:0,y:0,z:350},{x:0,y:0,z:0},900);};
document.getElementById('fit').onclick=()=>graph.zoomToFit(650,65);
document.getElementById('expand').onclick=()=>{allNodes.filter(n=>n.kind==='source'||n.kind==='group').forEach(n=>expanded.add(n.id));refresh();setTimeout(()=>graph.zoomToFit(650,60),500);};
document.getElementById('search').oninput=e=>{const q=e.target.value.toLowerCase().trim();if(!q)return;const n=graph.graphData().nodes.find(n=>n.label.toLowerCase().includes(q)||n.ticker?.toLowerCase().includes(q));if(n)graph.cameraPosition({x:n.x+65,y:n.y+30,z:n.z+75},n,600);};
new ResizeObserver(()=>{graph.width(el.clientWidth);graph.height(el.clientHeight)}).observe(el);
})();
</script></body></html>'''

def render():
    from capital_network import fetch_layer
    import country_market_data
    st.title('Global Market Intelligence · 3D Knowledge Graph')
    st.caption('Interactive market relationships · no company nodes or constituent holdings · peer-relative scores, not capital flows')
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
    st.caption(f"{len(payload['nodes'])} nodes · {len(payload['links'])} verified category relationships · double-click groups to expand/collapse")
    components.html(HTML.replace('__PAYLOAD__',json.dumps(payload).replace('</','<\\/')),height=750,scrolling=False)
    if errors:
        with st.expander(f'Unavailable market sources ({len(errors)})'):
            for source,error in errors.items():st.caption(f'{source}: {error}')
    st.caption('Connections indicate verified market-series membership in a source category. ETF price proxies do not establish fund holdings or company relationships. The 3D renderer loads JavaScript libraries from a public CDN.')
