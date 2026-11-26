"""Additional Streamlit section; existing research views remain untouched."""
import streamlit as st
import pandas as pd
from maketdata_bridge import fetch, metrics, score_universe, DEFAULT_WEIGHTS

def render_maketdata():
    st.divider()
    st.subheader('MaketData · MongoDB Fundamental Analysis')
    st.caption('Read-only Atlas data · Independent fundamental scores · Missing values remain N/A')
    initial=st.session_state.get('research_loaded') or st.session_state.get('research_ticker') or 'AAPL'
    raw=st.text_input('US stock tickers for comparison',value=str(initial),help='Comma-separated; existing research ticker is prefilled',key='maketdata_tickers')
    tickers=[s.strip().upper() for s in raw.split(',') if s.strip()][:30]
    if not st.button('Fetch MaketData fundamentals',key='maketdata_fetch'):return
    if not tickers:st.warning('Select at least one ticker.');return
    try:
        data=fetch(tickers)
    except Exception as exc:
        st.error('MongoDB retrieval failed. Check read-only user permissions, network access, and Streamlit Secrets.')
        st.caption(f'Connection diagnostic: {type(exc).__name__}')
        return
    missing=sorted(set(tickers)-set(data))
    if missing:st.warning('Not found in MaketData: '+', '.join(missing))
    if not data:return
    observations={}; period_counts={}
    for ticker, entry in data.items():
        observations[ticker],period_counts[ticker]=metrics(entry)
    # Show fundamentals even when valuation unavailable; do not invent market quotes.
    st.dataframe(pd.DataFrame(observations).rename_axis('Metric'),use_container_width=True)
    st.caption('Valuation fields require verified prices and market caps. Without these, scores remain N/A.')
    st.write('Annual periods retrieved:',period_counts)
    if len(observations)<2:
        st.info('Peer-relative scores require at least two companies with comparable validated observations.')
        return
    with st.expander('Fundamental score weights'):
        weights={k:st.number_input(k,min_value=0,max_value=100,value=int(v*100),step=5,key='maketdata_weight_'+k)/100 for k,v in DEFAULT_WEIGHTS.items()}
    if abs(sum(weights.values())-1)>1e-6:
        st.warning('Weights must total 100%.');return
    scored=score_universe(observations,weights)
    table=pd.DataFrame({t:{'Score':v['score'],'Coverage':v['coverage'],**v['categories']} for t,v in scored.items()}).T
    table['Rank']=table['Score'].rank(ascending=False,method='min')
    st.dataframe(table.sort_values('Rank',na_position='last'),use_container_width=True)
    st.caption('N/A — Insufficient Validated Data. Peer universe: '+str(len(observations))+' selected companies. Scores are separate from existing industry-cycle rankings.')
    with st.expander('Historical annual and quarterly financial statements'):
        for ticker, entry in data.items():
            st.markdown('**'+ticker+'**')
            for period in ('annual','quarterly'):
                st.caption(period.title())
                rows=[{'Period end':r.get('period_end'),**(r.get('metrics') or {})} for r in entry.get(period,[])]
                st.dataframe(pd.DataFrame(rows),use_container_width=True) if rows else st.info('No '+period+' records')
