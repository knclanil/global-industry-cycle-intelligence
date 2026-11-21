"""USA Investment Opportunity Screener, based on verified USA-only iShares membership."""
import pandas as pd
import streamlit as st
from usa_research_data import load_research, items, filter_companies, summary_table


def render_usa_opportunities():
    st.title('🇺🇸 USA Investment Opportunity Screener')
    st.caption('Assets → Sectors → Factors → Verified companies → Fundamentals → Valuation. Research, not investment advice.')
    frame,origin=load_research()
    if frame.empty:
        st.warning(origin)
        return
    st.caption(f'{origin} · U.S. issuers only · one row per verified issuer · no estimated financial data')
    c=st.columns(4)
    c[0].metric('Verified companies',len(frame))
    c[1].metric('Financial profiles',int(frame.fundamental_ready.eq('Yes').sum()))
    c[2].metric('Valuation profiles',int(frame.valuation_ready.eq('Yes').sum()))
    c[3].metric('Fully scored',int(frame.research_score.notna().sum()))
    sectors=sorted(set().union(*(items(s) for s in frame.sectors)))
    factors=sorted(set().union(*(items(s) for s in frame.factors)))
    funds=sorted(set().union(*(items(s) for s in frame.funds)))
    a,b,c=st.columns([2,2,1])
    sel_s=a.multiselect('Sectors',sectors,key='uo_s')
    sel_f=b.multiselect('Factors',factors,key='uo_f')
    mode=c.radio('Within each selection', ['ANY','ALL'],horizontal=True,key='uo_mode')
    d,e=st.columns(2)
    sel_funds=d.multiselect('Verified iShares ETFs',funds,key='uo_funds')
    query=e.text_input('Company or ticker',key='uo_search')
    x,y,z=st.columns(3)
    only_f=x.checkbox('Usable fundamentals',key='uo_only_f')
    only_v=y.checkbox('Usable valuations',key='uo_only_v')
    only_s=z.checkbox('Fully scored',key='uo_only_s')
    data=filter_companies(frame,sel_s,sel_f,sel_funds,mode,query,only_f,only_v,only_s)
    order=st.selectbox('Order by',['Research score','Company name','Factor breadth','Sector breadth'],key='uo_order')
    if order=='Research score':data=data.sort_values(['research_score','company'],ascending=[False,True],na_position='last')
    elif order=='Factor breadth':data=data.sort_values(['factor_count','company'],ascending=[False,True])
    elif order=='Sector breadth':data=data.sort_values(['sector_count','company'],ascending=[False,True])
    else:data=data.sort_values('company')
    st.caption(f'{len(data)} matching companies. AND between Sector/Factor/ETF groups; {mode} within a group.')
    if data.empty:
        st.info('No matching companies. Adjust the filters or check missing-data restrictions.')
        return
    st.dataframe(summary_table(data),hide_index=True,use_container_width=True,height=480)
    st.download_button('Download filtered research CSV',data.to_csv(index=False).encode(),
                       file_name='usa_opportunities.csv',mime='text/csv',key='uo_download')
    labels={str(r.company_key):f'{r.company} ({r.ticker})' for r in data.itertuples()}
    key=st.selectbox('Select company for deeper research',data.company_key.tolist(),format_func=lambda k:labels[str(k)],key='uo_company')
    if st.button('🔎 Open USA Company Deep Dive',type='primary',key='uo_to_detail'):
        st.session_state.usa_research_company_key=str(key)
        st.session_state.selected_page='USA Company Deep Dive'
        st.rerun()
    with st.expander('Methodology and data limitations'):
        st.write('ETF sector and factor memberships are evidence of holdings, not independent fundamental scores. ' 
                 'This page uses verified U.S. holdings only, excluding the Global fund universe and non-U.S. issuers. ' 
                 'Average ETF weight is an arithmetic mean of source ETF position weights, not portfolio allocation.')
        st.write('SEC financial facts are used only from cached companyfacts. No valuation score or cheap/expensive label ' 
                 'appears unless defensible price and same-period comparable peer data are available. ' 
                 'Missing data remains missing. Banks require sector-specific metrics.')
