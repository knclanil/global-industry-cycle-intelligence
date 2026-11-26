"""Sector/factor-level knowledge graph; never loads company or constituent records."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
ROOT=Path(__file__).resolve().parent/'data/dashboard_cache/rotation_graphs'
COLORS={'Leading':'#31d4a1','Improving':'#62a9ff','Weakening':'#ffc44d','Lagging':'#f17692'}
@st.cache_data(show_spinner=False)
def load(region,lookback):
 p=ROOT/f'{region.lower()}_{lookback}_signals.csv'
 if not p.exists():return pd.DataFrame()
 df=pd.read_csv(p)
 return df[df['kind'].astype(str).str.lower().isin(['sector','factor'])].copy()
def render_aggregate_graph(region):
 st.title(f'{region} · Sector & Factor Knowledge Graph')
 st.caption('Index-level sector/factor rotation only. No individual companies, tickers, SEC fundamentals or constituent holdings.')
 period=st.radio('Lookback',['1m','3m','6m'],index=1,horizontal=True,key='graph_period_'+region)
 df=load(region,period)
 if df.empty:
  st.warning('No sector/factor rotation snapshot found for this region and lookback.')
  return
 df['quadrant']=df['quadrant'].fillna('Unclassified')
 c1,c2,c3=st.columns(3)
 c1.metric('Tracked indices',len(df));c2.metric('Sector indices',sum(df.kind=='sector'));c3.metric('Factor indices',sum(df.kind=='factor'))
 fig=go.Figure()
 for kind,shape in [('sector','circle'),('factor','diamond')]:
  sub=df[df.kind==kind]
  for quadrant,part in sub.groupby('quadrant'):
   fig.add_trace(go.Scatter(x=pd.to_numeric(part.relative_strength,errors='coerce'),y=pd.to_numeric(part.rs_momentum,errors='coerce'),mode='markers+text',name=f'{kind.title()} · {quadrant}',text=part.source_id,textposition='top center',marker=dict(symbol=shape,size=13,color=COLORS.get(quadrant,'#aab6c8')),customdata=part[['label','as_of']].to_numpy(),hovertemplate='%{customdata[0]}<br>Relative strength: %{x:.2f}<br>Momentum: %{y:.2f}<br>As of: %{customdata[1]}<extra></extra>'))
 fig.add_vline(x=0,line_dash='dash',line_color='#64748b');fig.add_hline(y=0,line_dash='dash',line_color='#64748b')
 fig.update_layout(template='plotly_dark',paper_bgcolor='#142137',plot_bgcolor='#142137',height=620,xaxis_title='Relative strength',yaxis_title='RS momentum')
 st.plotly_chart(fig,use_container_width=True)
 st.subheader('Sector / factor rotation evidence')
 st.dataframe(df[['kind','source_id','label','quadrant','relative_strength','rs_momentum','as_of']].sort_values(['kind','label']),hide_index=True,use_container_width=True)
