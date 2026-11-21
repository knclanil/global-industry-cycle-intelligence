"""India single-company fundamentals, valuation context and traceable membership evidence."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from india_research_data import load_research, terms


def _display(value, percent=False):
    try:
        n=float(value)
        if pd.isna(n):return 'N/A'
        if percent:return f'{100*n:,.2f}%'
        return f'{n:,.2f}'
    except (TypeError,ValueError):
        return 'N/A'


def render_india_company_deep_dive():
    st.title('🇮🇳 Company Deep Dive')
    st.caption('Company fundamentals and valuation evidence, matched to verified NSE index memberships.')
    df, origin = load_research()
    if df.empty:
        st.warning(f'Company dataset unavailable: {origin}');return
    if st.button('← Back to Investment Opportunity Screener', key='id_back'):
        st.session_state.selected_page = 'India Investment Opportunity Screener'
        st.rerun()
    records=df.sort_values('company')
    keys=records.company_key.tolist()
    names={r.company_key:f'{r.company} ({r.ticker})' for r in records.itertuples()}
    initial=st.session_state.get('india_research_company_key')
    idx=keys.index(initial) if initial in keys else 0
    selected=st.selectbox('Find a company', keys, index=idx, format_func=lambda k:names.get(k,k),key='id_company_selector')
    st.session_state.india_research_company_key=selected
    r=records.loc[records.company_key==selected].iloc[0]
    st.subheader(f"{r['company']} · {r['ticker']}")
    st.caption(f"ISIN: {r['isin'] or 'Not available'} · Industry: {r['industry'] or 'Not classified'} · Source: {origin}")
    cols=st.columns(4)
    cols[0].metric('Quality', _display(r['quality_score']))
    cols[1].metric('Growth', _display(r['growth_score']))
    cols[2].metric('Valuation', _display(r['valuation_score']))
    cols[3].metric('Research score', _display(r['research_score']))
    if pd.isna(r['research_score']):
        st.warning('Insufficient comparable financial or valuation evidence for a research score. This is not a negative investment rating.')
    st.markdown('### Verified market memberships')
    c1,c2,c3=st.columns(3)
    c1.metric('Sector families/indexes', len(terms(r['sectors'])))
    c2.metric('Factor families',len(terms(r['factors'])))
    c3.metric('Source indexes',len(terms(r['source_indices'])))
    for title,key in [('Sectors','sectors'),('Factors','factors'),('Verified source indexes','source_indices')]:
        values=sorted(terms(r[key]))
        st.markdown(f"**{title}:** " + (' · '.join(values) if values else 'No verified memberships in tracked sources'))
    st.caption('Factor index membership is not independent verification of financial strength or cheap valuation. '
               'This page does not infer company rotation quadrants from memberships.')

    st.markdown('### Financial quality and growth')
    quality=[('Revenue','revenue',False),('Net income','net_income',False),
             ('Return on equity','roe',True),('Operating margin','operating_margin',True),
             ('Revenue growth YoY','revenue_yoy',True),('Earnings growth YoY','earnings_yoy',True),
             ('Operating cash flow','operating_cash_flow',False),('Free cash flow','free_cash_flow',False),
             ('Debt / equity','debt_to_equity',False)]
    st.dataframe(pd.DataFrame([{'Metric':title,'Value':_display(r[key],pct)} for title,key,pct in quality]),
                 hide_index=True,use_container_width=True)
    st.markdown('### Valuation and market data')
    val=[('Quote price','price',False),('Market cap','market_cap',False),('P/E','pe',False),
         ('P/B','pb',False),('EV / EBITDA','ev_to_ebitda',False),('Free cash flow yield','fcf_yield',True)]
    st.dataframe(pd.DataFrame([{'Metric':title,'Value':_display(r[key],pct)} for title,key,pct in val]),
                 hide_index=True,use_container_width=True)

    st.markdown('### Within-industry peer context')
    peer_group=r['peer_group']
    peers=df[(df.peer_group==peer_group)&(df.company_key!=selected)].copy()
    st.caption(f"Peer group: {peer_group or 'Unknown'} · {len(peers)} other tracked companies. "
               'Comparisons are exploratory and depend on reported data availability.')
    if peers.empty:
        st.info('No tracked peers available in this group.')
    else:
        peer_cols=['company','ticker','roe','pe','pb','research_score']
        ranked=pd.concat([df.loc[df.company_key==selected,peer_cols],peers[peer_cols]],ignore_index=True)
        ranked=ranked.sort_values('research_score',ascending=False,na_position='last')
        st.dataframe(ranked.rename(columns={'company':'Company','ticker':'Ticker','roe':'ROE (fraction)',
                        'pe':'P/E','pb':'P/B','research_score':'Research score'}),
                     hide_index=True,use_container_width=True,height=300)

    with st.expander('Financial statement dates, data gaps and source traceability',expanded=True):
        evidence=[('Income statement period','income_period'),('Balance sheet period','balance_period'),
                  ('Cash flow period','cashflow_period'),('Quote as of','quote_asof'),
                  ('Retrieved UTC','retrieved_utc'),('Missing KPI fields','coverage_flags'),
                  ('Scoring readiness','readiness_reason')]
        st.dataframe(pd.DataFrame([{'Evidence':title,'Value':str(r.get(key,'') or 'Unavailable')}
                                   for title,key in evidence]),hide_index=True,use_container_width=True)
        ticker=str(r['ticker']).strip()
        if ticker:
            st.markdown('Independent reporting reference: '
                        f'[Screener.in company page](https://www.screener.in/company/{ticker}/consolidated/)')
        st.caption('The cached Yahoo Finance statements may be standalone or consolidated. '
                   'No live company data requests occur on this page. Values are as reported in source currency/units; '
                   'cross-company nominal currency amounts should not be compared without normalization.')
