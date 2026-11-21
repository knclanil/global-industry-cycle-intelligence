"""Read-only India opportunity research: verified memberships x dated fundamentals.

No external requests. Missing data never assigned optimistic scores.
"""
from pathlib import Path
import json
import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'india_financials'

@st.cache_data(show_spinner=False, max_entries=8)
def _load(path,mtime):
    return pd.read_csv(path,keep_default_na=False)

def render_india_opportunities():
    st.subheader('India Investment Opportunity Research')
    st.caption('Verified NSE memberships · cached Yahoo financial evidence · transparent within-industry comparison. Research only, not a buy/sell signal.')
    path=DATA/'opportunity_research.csv'
    report_path=DATA/'opportunity_build_report.json'
    if not path.exists():
        st.warning('Opportunity dataset is not published yet. Run the India Company Financials Refresh workflow to collect, audit, and build it.')
        return
    df=_load(str(path),path.stat().st_mtime_ns)
    if df.empty:
        st.warning('No NSE company research records available.');return
    report=json.loads(report_path.read_text()) if report_path.exists() else {}
    cols=st.columns(4)
    cols[0].metric('Verified universe',len(df))
    cols[1].metric('Fundamentals ready',int((df['fundamental_ready']=='Yes').sum()))
    cols[2].metric('Valuation ready',int((df['valuation_ready']=='Yes').sum()))
    cols[3].metric('Fully scored',pd.to_numeric(df['research_score'],errors='coerce').notna().sum())
    if not pd.to_numeric(df['research_score'],errors='coerce').notna().any():
        st.info('No company qualifies for comparative scoring yet. Membership discovery still works; missing financial fields remain blank. Check the provider coverage report.')
    st.caption('Generated: '+str(report.get('generated_utc','unknown'))+' | Source scope: Yahoo Finance statements not independently verified as consolidated.')
    st.markdown('#### Find companies by verified index membership')
    universe_sectors=sorted({name.strip() for raw in df['sectors'].fillna('') for name in str(raw).split('|') if name.strip()})
    universe_factors=sorted({name.strip() for raw in df['factors'].fillna('') for name in str(raw).split('|') if name.strip()})
    c1,c2,c3=st.columns([2,2,1])
    sectors=c1.multiselect('Sectors (NSE sector indices)',universe_sectors,key='india_opportunity_sectors')
    factors=c2.multiselect('Factors (verified index families)',universe_factors,key='india_opportunity_factors')
    match=c3.radio('Within each selection',['ANY','ALL'],horizontal=True,key='india_opportunity_match')
    c4,c5,c6=st.columns([1,1,2])
    require_fin=c4.checkbox('Usable financials only',value=False,key='india_opportunity_fin_ready')
    scored=c5.checkbox('Fully scored only',value=False,key='india_opportunity_scored_only')
    query=c6.text_input('Search company or ticker',key='india_opportunity_query')
    def matches(raw,terms):
        if not terms:return True
        value=set(x.strip() for x in str(raw).split('|') if x.strip())
        return all(s in value for s in terms) if match=='ALL' else any(s in value for s in terms)
    view=df[df['sectors'].apply(lambda s:matches(s,sectors)) & df['factors'].apply(lambda s:matches(s,factors))].copy()
    if require_fin:view=view[view['fundamental_ready']=='Yes']
    if scored:view=view[pd.to_numeric(view['research_score'],errors='coerce').notna()]
    if query:
        view=view[view['company'].str.contains(query,case=False,regex=False) | view['ticker'].str.contains(query,case=False,regex=False)]
    st.caption(f'{len(view)} unique companies meet your selections. Sector and factor filters combine as AND; ANY/ALL operates within each filter.')
    show=['company','ticker','industry','sectors','factors','factor_count','sector_count','roe','revenue_yoy','pe','pb','quality_score','growth_score','valuation_score','research_score','research_ready','readiness_reason']
    numeric=['roe','revenue_yoy','pe','pb','quality_score','growth_score','valuation_score','research_score']
    for n in numeric:view[n]=pd.to_numeric(view[n],errors='coerce')
    view['roe']=view['roe']*100;view['revenue_yoy']=view['revenue_yoy']*100
    renamed={'company':'Company','ticker':'Ticker','industry':'Industry','sectors':'Sector memberships','factors':'Factor memberships',
             'factor_count':'# Factors','sector_count':'# Sectors','roe':'ROE %','revenue_yoy':'Revenue growth %',
             'pe':'P/E','pb':'P/B','quality_score':'Quality','growth_score':'Growth','valuation_score':'Valuation',
             'research_score':'Research score','research_ready':'Fresh & ready','readiness_reason':'Data quality / scoring gaps'}
    st.dataframe(view[show].rename(columns=renamed),use_container_width=True,hide_index=True,height=470)
    st.download_button('⬇ Export filtered research results',view.to_csv(index=False).encode('utf-8'),file_name='india_opportunity_research_filtered.csv',mime='text/csv',key='india_opportunity_export')
    with st.expander('Research one company — source evidence and data availability'):
        options=view['company_key'].tolist()
        if options:
            label_map=dict(zip(view['company_key'],view['company']+' ('+view['ticker']+')'))
            key=st.selectbox('Select company',options,format_func=lambda x:label_map[x],key='india_opportunity_company')
            r=df[df['company_key']==key].iloc[0]
            detail=['ticker','isin','industry','sectors','factors','source_indices','income_period','balance_period','cashflow_period','quote_asof','retrieved_utc','financial_fresh','quote_fresh','coverage_flags','readiness_reason','peer_group','peer_count']
            st.dataframe(pd.DataFrame({'Field':detail,'Value':[r.get(k,'') for k in detail]}),hide_index=True,use_container_width=True)
            sym=r['ticker']
            if sym:
                st.markdown('**Independent financial statement reference:** '+f'https://www.screener.in/company/{sym}/consolidated/')
    with st.expander('Model methodology and coverage'):
        st.write('Quality, growth, and valuation are independent observed-metric percentile comparisons against companies in the same reported industry. Financial companies have separate ROE and P/B/P/E rules. At least five OTHER companies must have a comparable metric; missing comparisons produce no score. Negative P/E and P/B are not treated as cheap.')
        st.write('Combined research score = 45% Quality + 20% Growth + 35% Valuation, only when statement age ≤540 days, quote age ≤30 days, minimum KPI coverage and peer comparisons pass. Scores are exploratory, not backtested predictions. No sector/factor rotation contribution is asserted.')
        st.write('Financial statements may be consolidated or standalone; no automatic Screener.in extraction. Index weights missing from NSE cannot be inferred.')
        cov=DATA/'kpi_coverage_report.json'
        if cov.exists():st.json(json.loads(cov.read_text()))
