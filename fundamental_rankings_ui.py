"""Compact dark-theme quality and consistency research rankings."""
import pandas as pd
import streamlit as st
from fundamental_rankings_engine import get_rankings, WEIGHTS, DATA


def _snapshot_token():
    locations = [DATA / 'india_financials' / 'companies', DATA / 'fundamentals', DATA / 'holdings']
    # A bounded directory scan; avoid parsing source facts during widget redraws.
    return tuple((str(p), p.stat().st_mtime_ns) for d in locations if d.exists() for p in d.glob('*.json')) + tuple((str(p), p.stat().st_mtime_ns) for p in (DATA / 'holdings').glob('*.parquet')) if (DATA / 'holdings').exists() else ()


@st.cache_data(show_spinner=False, ttl=900)
def _load(region, token):
    return get_rankings(region)


def render_fundamental_rankings():
    st.markdown('## ◈ Fundamental Quality & Consistency')
    st.caption('Multi-year company fundamentals · Separate from market leadership and stock valuation')
    region = st.segmented_control('Market', ['USA', 'Global', 'India'], default='USA', key='fundamental_rank_region') or 'USA'
    with st.spinner('Reading saved company financial statements…'):
        df = _load(region, _snapshot_token())
    if df.empty:
        st.warning('No matching saved financial statements available for this market. Run the existing SEC or India financial refresh; no values are estimated.')
        if region == 'Global':
            st.info('Global currently covers only verified SEC-reporting companies in Global ETF holdings. Other international issuers require a licensed global financial source.')
        return
    ranked = df[df.Status.eq('Ranked')]
    a,b,c,d = st.columns(4)
    a.metric('Financial snapshots', len(df))
    b.metric('Ranked companies', len(ranked))
    c.metric('Awaiting data / history', len(df)-len(ranked))
    d.metric('Source coverage', f'{100*len(ranked)/len(df):.0f}%')
    s1,s2,s3 = st.tabs(['Company rankings', 'History & methodology', 'Intrinsic & Graham value'])
    with s1:
        f1,f2=st.columns([2,1])
        text=f1.text_input('Search company', placeholder='Ticker or name', key=f'fund_search_{region}')
        include=f2.toggle('Show incomplete coverage', value=False)
        view=df if include else ranked
        if text:
            view=view[view.Ticker.fillna('').str.contains(text, case=False, regex=False) | view.Company.fillna('').str.contains(text, case=False, regex=False)]
        metrics=['ROE','Debt / equity','Current ratio','Operating margin','Net margin','Revenue growth','Liabilities / assets','Dividend consistency','Dividend growth']
        cols=['Rank','Ticker','Company','Sector','Fundamental score','Consistency','Years','Metric coverage %'] + metrics + (['Status'] if include else [])
        config={
            'Fundamental score':st.column_config.ProgressColumn('Quality / 100', min_value=0,max_value=100,format='%.1f'),
            'Consistency':st.column_config.NumberColumn('Consistency / 100',format='%.1f'),
            'Metric coverage %':st.column_config.NumberColumn('Coverage',format='%.1f%%'),
            **{m:st.column_config.NumberColumn(m,format='%.2f') for m in ['Debt / equity','Current ratio']},
            **{m:st.column_config.NumberColumn(m,format='%.2f%%') for m in ['ROE','Operating margin','Net margin','Revenue growth','Liabilities / assets','Dividend consistency','Dividend growth']},
        }
        # Financial ratios stored as fractions; format them in percentage points
        # without altering underlying exported raw data.
        shown=view.copy()
        for metric in ['ROE','Operating margin','Net margin','Revenue growth','Liabilities / assets','Dividend consistency','Dividend growth']:
            shown[metric]=pd.to_numeric(shown[metric], errors='coerce')*100
        st.dataframe(shown[[c for c in cols if c in shown]],hide_index=True,use_container_width=True,column_config=config,height=520)
        st.download_button('Export all company fundamental data',df.drop(columns=['History'],errors='ignore').to_csv(index=False),
                           file_name=f'{region.lower()}_fundamental_quality.csv',mime='text/csv')
    with s2:
        choices=df[['Ticker','Company']].drop_duplicates().copy()
        choices['label']=choices['Ticker'].fillna('')+' · '+choices['Company'].fillna('')
        selected=st.selectbox('Company history', choices['label'].to_list())
        sym=choices.loc[choices.label.eq(selected),'Ticker'].iloc[0]
        row=df.loc[df.Ticker.eq(sym)].iloc[0]
        history=pd.DataFrame(row.get('History',[]))
        if not history.empty:
            history['date']=pd.to_datetime(history['date'],errors='coerce')
            st.line_chart(history.set_index('date')[[c for c in ['revenue','net_income','operating_income'] if c in history]])
            st.dataframe(history.sort_values('date',ascending=False),use_container_width=True,hide_index=True)
        st.caption(f"Financial source: {row.get('Source','N/A')} · Latest fiscal period: {row.get('As of','N/A')} · Historical reporting periods: {int(row.get('Years',0))}")
        with st.expander('Ranking methodology'):
            st.markdown('Company quality is ranked using the median of up to five annual observations. A peer-group percentile is computed within each region and sector only when at least five firms report the metric. Eligible firms need at least three years, five supported metrics, 60% weighted coverage, and stability data. Score = 85% covered-metric percentiles + 15% stability. The score is not valuation or a buy recommendation.')
            st.dataframe(pd.DataFrame({'Financial metric':list(WEIGHTS),'Weight %':[round(v*100) for v in WEIGHTS.values()]}),hide_index=True,use_container_width=True)
            st.caption('Dividend consistency is only assessed with three reported annual dividend cash-flow observations. Banks and insurers may need industry-specific models; any metrics lacking comparable peer coverage remain unranked. Global non-US issuers are not assumed to have SEC fundamentals.')
    with s3:
        st.caption('Saved annual statements · Calculated EPS from net income and reported shares · No website EPS')
        value_cols = ['Rank','Ticker','Company','Sector','Calculated EPS','FCF / share','Book value / share',
                      'Graham number','DCF Bear','DCF Base','DCF Bull','FCF observations',
                      'EPS share basis','Valuation as of','Valuation note']
        available = [c for c in value_cols if c in df.columns]
        if len(available) <= 4:
            st.info('No valuation-ready historical statements found.')
        else:
            choice = st.text_input('Find company', key=f'value_find_{region}', placeholder='Ticker or company')
            values = df.copy()
            if choice:
                values = values[values.Ticker.fillna('').str.contains(choice,case=False,regex=False) |
                                values.Company.fillna('').str.contains(choice,case=False,regex=False)]
            money_unit = '₹' if region == 'India' else '$'
            configs = {k: st.column_config.NumberColumn(k + ' (' + money_unit + ')', format='%.2f')
                       for k in ('Calculated EPS','FCF / share','Book value / share','Graham number',
                                 'DCF Bear','DCF Base','DCF Bull') if k in values}
            st.dataframe(values[available], hide_index=True, use_container_width=True,
                         height=480, column_config=configs)
            st.download_button('Export company valuation estimates',
                               values[available].to_csv(index=False),
                               file_name=f'{region.lower()}_company_valuations.csv', mime='text/csv')
        with st.expander('Valuation definitions & required financial inputs'):
            st.markdown('''
**Calculated EPS** = reported annual net income / reported weighted-average common shares. Where only period-end ordinary shares are available, EPS is labeled an approximation. EPS is accounting earnings, **not cash** or website-reported EPS. A separate **FCF / share** figure shows operating cash flow minus capex divided by shares.

**Graham Number** = sqrt(22.5 × calculated EPS × book value per common share). Requires positive EPS and book value. This is a screening heuristic, not guaranteed fair value.

**DCF Bear / Base / Bull** = illustrative five-year discounted normalized historical operating cash flow minus capital expenditure, per share. Bear: 0% growth / 12% discount / 2% terminal; Base: 3% / 11% / 3%; Bull: 5% / 10% / 3.5%. Requires at least three recent consecutive years with positive FCF and valid shares. This is a simplified FCF proxy, **not** a fully adjusted FCFE or enterprise valuation.

Fiscal period, share basis, and sources are displayed. Missing financial inputs are N/A. The existing fundamental quality ranking is **not changed** by valuations.
            ''')
