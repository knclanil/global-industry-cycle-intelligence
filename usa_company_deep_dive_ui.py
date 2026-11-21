"""USA company details: verified holdings plus existing SEC research drilldown."""
import pandas as pd
import streamlit as st
from usa_research_data import load_research,items


def fmt(v,pct=False):
    try:
        if pd.isna(v):return 'N/A'
        return f'{float(v)*100:,.2f}%' if pct else f'{float(v):,.2f}'
    except (TypeError,ValueError):return 'N/A'


def render_usa_company_deep_dive():
    st.title('🇺🇸 USA Company Deep Dive')
    if st.button('← Back to USA Investment Opportunity Screener',key='ud_back'):
        st.session_state.selected_page='USA Investment Opportunity Screener';st.rerun()
    df,origin=load_research()
    if df.empty:st.warning(origin);return
    df=df.sort_values('company')
    keys=df.company_key.astype(str).tolist()
    current=str(st.session_state.get('usa_research_company_key',''))
    idx=keys.index(current) if current in keys else 0
    names={str(r.company_key):f'{r.company} ({r.ticker})' for r in df.itertuples()}
    selected=st.selectbox('Company',keys,index=idx,format_func=lambda x:names[x],key='ud_company')
    st.session_state.usa_research_company_key=selected
    row=df.loc[df.company_key.astype(str)==selected].iloc[0]
    st.subheader(f"{row['company']} · {row['ticker']}")
    st.caption(f"Country: United States · Holdings as of: {row['holdings_asof'] or 'Unknown'} · {origin}")
    a,b,c=st.columns(3)
    a.metric('Sector families',len(items(row['sectors'])))
    b.metric('Factor families',len(items(row['factors'])))
    c.metric('Source ETFs',int(row['membership_count']))
    st.markdown('### Verified membership evidence')
    st.write('**Sectors:**',row['sectors'] or 'None')
    st.write('**Factors:**',row['factors'] or 'None')
    st.write('**Source funds:**',row['funds'] or 'None')
    st.caption('Fund exposure is not proof of company value, quality, or future returns.')
    st.markdown('### Financial and valuation evidence')
    metrics=[('Revenue','revenue',False),('Net income','net_income',False),
             ('Revenue YoY','revenue_yoy',True),('ROE','roe',True),
             ('Operating margin','operating_margin',True),('Operating cash flow','operating_cash_flow',False),
             ('Free cash flow','free_cash_flow',False),('Long-term debt / equity','debt_to_equity',False),
             ('P/E','pe',False),('P/B','pb',False),('Quality score','quality_score',False),
             ('Growth score','growth_score',False),('Valuation score','valuation_score',False),
             ('Research score','research_score',False)]
    st.dataframe(pd.DataFrame([{'Metric':label,'Value':fmt(row[key],pct)} for label,key,pct in metrics]),
                 hide_index=True,use_container_width=True)
    if pd.isna(row['research_score']):
        st.info('No composite investment score: comparable pricing / valuation evidence is not established. ' 
                'Use SEC filing data below for independent analysis.')
    st.caption(f"SEC financial period: {row['financial_period'] or 'Not cached'} · "
               f"CIK: {row['sec_cik'] or 'Not mapped'} · {row['readiness_reason'] or 'Coverage incomplete'}")
    st.markdown('### Full SEC financial research')
    st.caption('Uses the existing SEC Financial Research page, including annual and quarterly statements, ' 
               'cash flows, valuation assumptions and reporting diagnostics.')
    if st.button('Open full SEC financial research',type='primary',key='ud_sec'):
        st.session_state.research_ticker=str(row['ticker']).upper()
        st.session_state.research_loaded=str(row['ticker']).upper()
        st.session_state.selected_page='Company Financial Research'
        st.rerun()
    if st.button('Open USA Financial KPIs',key='ud_kpis'):
        st.session_state.kpi_ticker=str(row['ticker']).upper()
        st.session_state.kpi_loaded=str(row['ticker']).upper()
        st.session_state.selected_page='USA Company Financial KPI Intelligence'
        st.rerun()
