from pathlib import Path
import json
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
ROOT=Path(__file__).parent
st.set_page_config(page_title='Global Industry Cycle Intelligence',page_icon='🌐',layout='wide')
st.markdown('''<style>.block-container{padding-top:1.5rem;max-width:1500px}h1,h2,h3{letter-spacing:-.03em}div[data-testid="stMetric"]{background:#142438;border:1px solid #29415a;border-radius:12px;padding:14px}</style>''',unsafe_allow_html=True)
@st.cache_data(ttl=600)
def load(name):
 p=ROOT/'data'/name
 return pd.read_parquet(p) if p.exists() else pd.DataFrame()
@st.cache_data(ttl=600)
def publications():
 p=ROOT/'data/publications.json'
 return pd.DataFrame(json.loads(p.read_text())) if p.exists() else pd.DataFrame()
@st.cache_data(ttl=600)
def instruments():return pd.read_csv(ROOT/'config/instruments.csv').fillna('')
S=load('sector_snapshot.parquet');H=load('sector_history.parquet');P=load('prices.parquet');I=instruments()
nav=st.sidebar.radio('NAVIGATION',['Cycle Overview','Cycle Explorer','Cross-Market Comparison','Leadership & Rotation','Opportunity Scanner','Knowledge Center'],label_visibility='visible')
st.sidebar.caption('INDIA  •  USA  •  GLOBAL')
st.sidebar.markdown('---')
st.sidebar.caption('Market cycle = price-based relative performance; not a forecast of industry earnings or economic conditions.')
if not S.empty: st.sidebar.caption('Latest available market observation: '+str(S.asof.max()))
else: st.sidebar.warning('No market observations yet. Run the GitHub workflow or scripts/collect_prices.py and scripts/analyze.py.')
def clean(df):return df.replace([np.inf,-np.inf],np.nan)
def fmt_table(df,columns=None):
 d=clean(df.copy());d=d[columns] if columns else d
 st.dataframe(d,use_container_width=True,hide_index=True)
def stage_colors(stage):return {'Leading':'#21bd9b','Improving':'#48a7e7','Weakening':'#f3b450','Lagging':'#ee6b72'}.get(stage,'#8996a9')
def stage_matrix(df):
 if df.empty:return
 pivot=df.pivot_table(index='sector',columns='market',values='stage',aggfunc='first').reindex(columns=['India','USA','Global'])
 def style(v):return f'background-color:{stage_colors(v)};color:#071321;font-weight:650' if isinstance(v,str) else ''
 st.dataframe(pivot.style.map(style),use_container_width=True)
def series_chart(market,sector,benchmark=True):
 if P.empty:return
 row=I[(I.market==market)&(I.sector==sector)]
 if row.empty:return
 t=row.iloc[0].ticker;b=row.iloc[0].benchmark
 df=P[P.ticker.isin([t,b])].copy()
 if df.empty:return
 df['date']=pd.to_datetime(df.date)
 w=df.pivot_table(index='date',columns='ticker',values='close').sort_index()
 if t not in w:return
 cols=[t]+([b] if benchmark and b in w and b!=t else [])
 w=w[cols].dropna()
 if w.empty:return
 w=w/w.iloc[0]*100
 fig=go.Figure()
 for col in w:fig.add_trace(go.Scatter(x=w.index,y=w[col],name=('Sector' if col==t else 'Benchmark'),mode='lines'))
 fig.update_layout(template='plotly_dark',height=400,yaxis_title='Indexed to 100',xaxis_title='',margin=dict(t=25,b=15))
 st.plotly_chart(fig,use_container_width=True)
if nav=='Cycle Overview':
 st.title('Global Industry Cycle Intelligence')
 st.caption('Market leadership across India, the USA and global sector proxies. Stage labels are market-relative, not fundamental economic-cycle diagnoses.')
 if S.empty:st.info('The dashboard is ready. No live data has been collected yet. See README for setup.')
 else:
  a,b,c,d=st.columns(4)
  a.metric('Sectors tracked',len(S));b.metric('Leading',int((S.stage=='Leading').sum()));c.metric('Improving',int((S.stage=='Improving').sum()));d.metric('Markets',S.market.nunique())
  st.subheader('Industry cycle matrix');stage_matrix(S)
  st.subheader('Market-cycle transitions')
  if not H.empty:
   h=H.sort_values('date');latest=h.groupby(['market','sector']).tail(2)
   change=latest.groupby(['market','sector']).filter(lambda x:len(x)==2 and x.stage.iloc[0]!=x.stage.iloc[-1]);last=change.groupby(['market','sector']).tail(1)
   fmt_table(last[['market','sector','date','stage','rs_6m','momentum_change']].round(2)) if not last.empty else st.caption('No recent monthly transitions detected.')
  st.subheader('Six-month relative performance (%)')
  fig=px.imshow(S.pivot(index='sector',columns='market',values='rs_6m').reindex(columns=['India','USA','Global']),color_continuous_scale='RdYlGn',color_continuous_midpoint=0,aspect='auto',text_auto='.1f')
  fig.update_layout(template='plotly_dark',height=470);st.plotly_chart(fig,use_container_width=True)
elif nav=='Cycle Explorer':
 st.title('Industry Cycle Explorer')
 market=st.selectbox('Market',['India','USA','Global'])
 sectors=sorted(I[I.market==market].sector.unique());sector=st.selectbox('Industry',sectors)
 st.caption('Historical market-relative cycle stages are estimated using 6-month excess return and 3-month momentum change.')
 row=S[(S.market==market)&(S.sector==sector)] if not S.empty else pd.DataFrame()
 if not row.empty:
  r=row.iloc[0];a,b,c,d=st.columns(4);a.metric('Stage',r.stage);b.metric('6M relative strength',f'{r.rs_6m:.1f}%' if pd.notna(r.rs_6m) else 'N/A');c.metric('3M return',f'{r.return_3m:.1f}%' if pd.notna(r.return_3m) else 'N/A');d.metric('RSI',f'{r.rsi:.0f}' if pd.notna(r.rsi) else 'N/A')
 st.subheader('Sector vs domestic / global benchmark');series_chart(market,sector)
 if not H.empty:
  h=H[(H.market==market)&(H.sector==sector)].copy();h['date']=pd.to_datetime(h.date)
  if not h.empty:
   st.subheader('Relative strength history');fig=px.line(h,x='date',y=['rs_3m','rs_6m'],labels={'value':'Excess return (percentage points)','date':'','variable':'Metric'},template='plotly_dark');st.plotly_chart(fig,use_container_width=True)
   st.subheader('Monthly cycle timeline');fmt_table(h[['date','stage','rs_6m','momentum_change']].tail(36).iloc[::-1].round(2))
 st.info('Fundamental industry cycle cannot be established from price data alone. See Knowledge Center for source-linked economic and industry evidence.')
elif nav=='Cross-Market Comparison':
 st.title('India vs USA vs Global')
 sector=st.selectbox('Comparable sector',sorted(I.sector.unique()))
 subset=S[S.sector==sector] if not S.empty else pd.DataFrame()
 if not subset.empty:
  st.subheader('Market leadership');fmt_table(subset[['market','ticker','source_type','stage','return_3m','return_6m','rs_3m','rs_6m','note']].round(2))
 if not P.empty:
  traces=[]
  for row in I[I.sector==sector].itertuples(index=False):
   x=P[P.ticker==row.ticker].copy();x['date']=pd.to_datetime(x.date);x=x.sort_values('date').set_index('date')['close']
   if len(x)<2:continue
   traces.append((row.market,x))
  if traces:
   st.subheader('Local-currency indexed performance (not FX adjusted)')
   common=max(x.index.min() for _,x in traces)
   fig=go.Figure()
   for name,x in traces:
    x=x[x.index>=common]
    if len(x)>1:fig.add_trace(go.Scatter(x=x.index,y=x/x.iloc[0]*100,name=name))
   fig.update_layout(template='plotly_dark',height=460,yaxis_title='Indexed to 100');st.plotly_chart(fig,use_container_width=True)
 st.warning('Cross-market index/ETF sector definitions and currencies differ. These charts show directional comparisons, not perfectly matched industry baskets. India has several approximate proxies; inspect the mapping table in Knowledge Center.')
 if not H.empty:
  st.subheader('Monthly market-cycle comparison');h=H[H.sector==sector].copy();fmt_table(h.sort_values('date',ascending=False)[['date','market','stage','rs_6m']].head(45).round(2))
elif nav=='Leadership & Rotation':
 st.title('Industry Leadership & Rotation')
 market=st.selectbox('Market',['India','USA','Global'])
 if not S.empty:
  x=S[S.market==market].sort_values('rs_6m',ascending=False)
  st.subheader('Relative-strength rankings');fmt_table(x[['sector','ticker','stage','return_1m','return_3m','return_6m','rs_1m','rs_3m','rs_6m','momentum_change','rsi']].round(2))
  fig=px.bar(x,x='rs_6m',y='sector',orientation='h',color='stage',color_discrete_map={k:stage_colors(k) for k in ['Leading','Improving','Weakening','Lagging']},template='plotly_dark');fig.update_layout(height=540,yaxis={'categoryorder':'total ascending'});st.plotly_chart(fig,use_container_width=True)
  st.subheader('Rotation quadrants')
  fig=px.scatter(x,x='rs_6m',y='momentum_change',color='stage',text='sector',color_discrete_map={k:stage_colors(k) for k in ['Leading','Improving','Weakening','Lagging']},template='plotly_dark')
  fig.add_vline(x=0,line_dash='dash');fig.add_hline(y=0,line_dash='dash');fig.update_traces(textposition='top center');fig.update_layout(height=580,xaxis_title='6M relative return (percentage points)',yaxis_title='Change in 3M relative return (percentage points)');st.plotly_chart(fig,use_container_width=True)
elif nav=='Opportunity Scanner':
 st.title('Cycle Opportunity Scanner')
 st.caption('Rule-based research candidates, not buy/sell signals. Signals use price data only.')
 strategy=st.selectbox('Screen',['Early recovery','Confirmed leadership','Weakening leader','Deep laggard','All industries'])
 market=st.multiselect('Markets',['India','USA','Global'],default=['India','USA','Global'])
 if not S.empty:
  x=S[S.market.isin(market)].copy()
  if strategy=='Early recovery':x=x[(x.rs_6m<0)&(x.rs_1m>0)&(x.rsi>50)]
  elif strategy=='Confirmed leadership':x=x[(x.rs_3m>0)&(x.rs_6m>0)&(x.rsi>50)]
  elif strategy=='Weakening leader':x=x[(x.rs_6m>0)&(x.momentum_change<0)]
  elif strategy=='Deep laggard':x=x[(x.rs_6m<0)&(x.momentum_change<0)]
  st.metric('Matches',len(x));fmt_table(x[['market','sector','ticker','stage','rs_1m','rs_3m','rs_6m','rsi','asof']].round(2)) if not x.empty else st.info('No sectors match the selected rules.')
  st.download_button('Download results (CSV)',x.to_csv(index=False).encode(),'cycle_screen.csv','text/csv')
else:
 st.title('Economic & Industry Intelligence — Knowledge Center')
 tabs=st.tabs(['Intelligence Feed','Country Wiki','Industry Wiki','Opportunity Radar','Publisher Library','Research Archive','Data & Methodology'])
 with tabs[0]:
  st.subheader('Newly discovered publisher items');q=publications()
  if q.empty:st.info('No RSS items collected yet. Run scripts/monitor_publishers.py or the scheduled workflow. Publisher entries without a feed are listed for manual monitoring.')
  else:
   market=st.selectbox('Region',['All','India','USA','Global'],key='feedmarket')
   if market!='All':q=q[q.market==market]
   search=st.text_input('Search titles and publishers')
   if search:q=q[q.title.str.contains(search,case=False,na=False)|q.publisher.str.contains(search,case=False,na=False)]
   for _,r in q.head(60).iterrows():
    st.markdown(f"**[{r['title']}]({r['url']})**  \n{r['publisher']} · {r['market']} · {r.get('published','') or 'Publication date not supplied'}")
   st.caption('These are source-discovered links, not AI-reviewed summaries or verified opportunity assessments.')
 with tabs[1]:
  country=st.selectbox('Country',['India','USA','Global'])
  file=ROOT/'knowledge/countries'/f'{country.lower()}.md'
  st.markdown(file.read_text() if file.exists() else 'No country article yet.')
 with tabs[2]:
  sector=st.selectbox('Sector',sorted(I.sector.unique()),key='wikiindustry')
  file=ROOT/'knowledge/industries'/f"{sector.lower().replace(' ','_')}.md"
  st.markdown(file.read_text() if file.exists() else 'Industry page awaiting sourced research. No claims have been generated.')
  st.subheader('Related market data');fmt_table(S[S.sector==sector][['market','ticker','stage','rs_6m','asof']].round(2)) if not S.empty else st.caption('No price data available.')
 with tabs[3]:
  st.subheader('Evidence-based opportunity watchlist')
  st.info('Price-based early recovery candidates appear below. Fundamental opportunity cards require manually reviewed, source-linked reports and are not fabricated.')
  if not S.empty:
   x=S[(S.rs_6m<0)&(S.rs_1m>0)&(S.rsi>50)]
   fmt_table(x[['market','sector','ticker','stage','rs_1m','rs_6m']].round(2)) if not x.empty else st.caption('No current matches.')
  p=ROOT/'knowledge/opportunities.json'
  if p.exists():
   for item in json.loads(p.read_text()):
    with st.expander(item.get('title','Opportunity')):
     st.write(item.get('hypothesis',''));st.write('Evidence:',item.get('evidence',[]));st.write('Risks:',item.get('risks',[]))
 with tabs[4]:
  pubs=json.loads((ROOT/'config/publishers.json').read_text())
  fmt_table(pd.DataFrame(pubs)[['name','market','industry','homepage','feed']]);st.caption('Only configured RSS/Atom feeds are automatically monitored. Homepage-only publishers are not automatically scraped.')
 with tabs[5]:
  q=publications()
  if q.empty:st.info('Archive will populate after successful feed monitoring.')
  else:
   fmt_table(q[['publisher','market','industry','title','published','discovered_utc','url','assessment']]);st.download_button('Export archive',q.to_csv(index=False),'research_archive.csv','text/csv')
 with tabs[6]:
  for name in ['methodology/market_cycle.md','methodology/limitations.md','methodology/architecture.md']:
   st.markdown((ROOT/'knowledge'/name).read_text())
  st.subheader('Instrument mappings');fmt_table(I)
  status=ROOT/'data/collection_status.json'
  if status.exists():st.json(json.loads(status.read_text()))
