"""India Investment Opportunity Screener — verified memberships with honest KPI gates."""
from __future__ import annotations
import streamlit as st
import pandas as pd
from india_research_data import (load_research, terms, filter_companies,
                                 format_summary, report)


def render_india_opportunities():
    st.title('🇮🇳 India Investment Opportunity Screener')
    st.caption('Assets → Sectors → Factors → Companies → Fundamentals → Valuation. '
               'Verified NSE company memberships and cached financial statements; not investment advice.')
    df, origin = load_research()
    if df.empty:
        st.warning(f'Company universe unavailable: {origin}. Run the India constituents and financial refresh workflows.')
        return
    st.caption(f'Data source: {origin} · one row per verified company identity · missing metrics are not estimated')
    k = st.columns(4)
    k[0].metric('Companies', len(df))
    k[1].metric('Fundamentals available', int((df.fundamental_ready == 'Yes').sum()))
    k[2].metric('Valuation available', int((df.valuation_ready == 'Yes').sum()))
    k[3].metric('Comparable research scores', int(df.research_score.notna().sum()))

    sectors = sorted(set.union(set(), *(terms(x) for x in df.sectors)))
    factors = sorted(set.union(set(), *(terms(x) for x in df.factors)))
    indices = sorted(set.union(set(), *(terms(x) for x in df.source_indices)))
    a,b,c = st.columns([2,2,1])
    chosen_sectors = a.multiselect('Sectors', sectors, key='io_sectors')
    chosen_factors = b.multiselect('Factors', factors, key='io_factors')
    match = c.radio('Within each group', ['ANY','ALL'], horizontal=True, key='io_match')
    d,e = st.columns([2,2])
    chosen_indices = d.multiselect('Verified source indexes', indices, key='io_indices')
    search = e.text_input('Company, ticker or ISIN', key='io_search')
    f1,f2,f3 = st.columns(3)
    only_fundamentals = f1.checkbox('Usable fundamentals', key='io_fund')
    only_valuations = f2.checkbox('Usable valuations', key='io_value')
    only_scored = f3.checkbox('Fully scored companies', key='io_scored')
    view = filter_companies(df, chosen_sectors, chosen_factors, chosen_indices, match,
                            search, only_fundamentals, only_valuations, only_scored)
    sort = st.selectbox('Sort companies', ['Research score (highest first)', 'Company A–Z',
                                          'Factor family count', 'Sector index count'], key='io_sort')
    if sort.startswith('Research'):
        view = view.sort_values(['research_score','company'], ascending=[False,True], na_position='last')
    elif sort.startswith('Company'):
        view = view.sort_values('company', key=lambda col:col.str.casefold())
    elif sort.startswith('Factor'):
        view = view.sort_values(['factor_count','company'], ascending=[False,True])
    else:
        view = view.sort_values(['sector_count','company'], ascending=[False,True])
    st.markdown('#### Companies matching your research criteria')
    st.caption(f'{len(view)} unique companies · filters across Sector / Factor / Index use AND; '
               f'{match} applies within each selected category. No companies are scored because of index membership alone.')
    if view.empty:
        st.info('No companies match these selections. Remove a filter or switch ALL to ANY.')
        return
    st.dataframe(format_summary(view), use_container_width=True, hide_index=True, height=500)
    st.download_button('⬇ Download filtered company research', view.to_csv(index=False).encode('utf-8'),
                       'india_company_opportunities.csv', 'text/csv', key='io_download')
    st.markdown('#### Continue to company research')
    company_keys = view.company_key.tolist()
    name_map = {str(r.company_key):f'{r.company} ({r.ticker})' for r in view.itertuples()}
    selected = st.selectbox('Choose a company', company_keys, format_func=lambda key:name_map.get(key,key),key='io_company')
    if st.button('🔎 Open Company Deep Dive', type='primary', key='io_open_detail'):
        st.session_state.india_research_company_key = selected
        st.session_state.selected_page = 'India Company Deep Dive'
        st.rerun()
    with st.expander('Scoring and missing-data methodology'):
        st.write('Quality 45%, Growth 20%, Valuation 35% where all three components are available and freshness gates pass. '
                 'Scores are cross-sectional comparisons within peer groups—not proven forecasts, buy signals, or sector rotation scores.')
        st.write('The underlying financial collection may lack income, cash flow, valuation or recent quotes. '
                 'Missing data remains missing; banks and insurers need industry-specific comparisons.')
        meta=report()
        if meta: st.json(meta)
