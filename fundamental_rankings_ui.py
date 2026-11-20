"""Compact dark-theme quality and consistency research rankings."""
import pandas as pd
import streamlit as st
from fundamental_rankings_engine import get_rankings, WEIGHTS, DATA, snapshot_comparison, load_india_reference_snapshot


def _snapshot_token():
    """Invalidate the UI cache whenever saved financial sources change."""
    locations = [DATA / 'india_financials', DATA / 'fundamentals', DATA / 'holdings']
    entries = []
    for folder in locations:
        if folder.exists():
            for extension in ('*.json', '*.csv', '*.parquet'):
                for p in folder.glob(extension):
                    entries.append((str(p), p.stat().st_mtime_ns, p.stat().st_size))
            # India financial company JSONs live one directory deeper.
            if (folder / 'companies').exists():
                for p in (folder / 'companies').glob('*.json'):
                    entries.append((str(p), p.stat().st_mtime_ns, p.stat().st_size))
    return tuple(sorted(entries))


@st.cache_data(show_spinner=False, ttl=900)
def _load(region, token):
    return get_rankings(region)


def render_fundamental_rankings():
    st.markdown('## ◈ Fundamental Quality & Consistency')
    st.caption('Five-dimension business quality · Financial-statement history · Valuations shown separately')
    region = st.segmented_control('Market', ['USA', 'Global', 'India'], default='USA', key='fundamental_rank_region') or 'USA'
    if region == 'India':
        _render_india_rankings()
        return
    with st.spinner('Reading saved company financial statements…'):
        df = _load(region, _snapshot_token())
    if df.empty:
        st.warning('No financial records found for this market. For India, check the attached reference snapshot or run the annual-statements refresh.')
        if region == 'Global':
            st.info('Global currently covers only verified SEC-reporting companies in Global ETF holdings. Other international issuers require a licensed global financial source.')
        return
    ranked = df[df.Status.eq('Ranked')]
    india_snapshot_only = region == 'India' and ranked.empty and (df['Years'].fillna(0) < 3).all()
    if india_snapshot_only:
        st.info('India: available provider ratio snapshots are displayed below, but no companies qualify for a multi-year quality rank yet. Three consecutive years of actual annual statements are required. Graham and DCF remain N/A without financial inputs.')
    a,b,c,d = st.columns(4)
    a.metric('Financial snapshots', len(df))
    b.metric('Ranked companies', len(ranked))
    c.metric('Awaiting data / history', len(df)-len(ranked))
    d.metric('Source coverage', f'{100*len(ranked)/len(df):.0f}%')
    s1,s2,s3 = st.tabs(['Company rankings', 'History & methodology', 'Intrinsic & Graham value'])
    with s1:
        f1,f2=st.columns([2,1])
        text=f1.text_input('Search company', placeholder='Ticker or name', key=f'fund_search_{region}')
        include=f2.toggle('Show incomplete coverage', value=india_snapshot_only)
        view=df if include else ranked
        if text:
            view=view[view.Ticker.fillna('').str.contains(text, case=False, regex=False) | view.Company.fillna('').str.contains(text, case=False, regex=False)]
        metrics=['ROE','Debt / equity','Current ratio','Operating margin','Net margin','Revenue CAGR','EPS CAGR','FCF margin','Cash conversion','Positive FCF years','Liabilities / assets','Dividend consistency']
        cols=['Rank','Ticker','Company','Sector','Fundamental score','Profitability & capital efficiency score','Financial strength score','Growth quality score','Cash flow quality score','Historical consistency score','Years','Metric coverage %'] + metrics + (['Source','Status'] if include else [])
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
        for metric in ['ROE','Operating margin','Net margin','Revenue CAGR','EPS CAGR','FCF margin','Liabilities / assets','Dividend consistency','Positive FCF years']:
            shown[metric]=pd.to_numeric(shown[metric], errors='coerce')*100
        st.dataframe(shown[[c for c in cols if c in shown]],hide_index=True,use_container_width=True,column_config=config,height=520)
        if region == 'India' and 'Financial data type' in df:
            with st.expander('India financial coverage & source limitations'):
                st.dataframe(df.groupby(['Source', 'Status'], dropna=False).size().rename('Companies').reset_index(), hide_index=True, use_container_width=True)
                st.caption('Single-period reference ratios may originate from NSE/Yahoo and have not been independently reconstructed from annual statements. They are displayed for research only, and cannot establish multi-year consistency or support statement-derived EPS, Graham or DCF values.')
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
            st.markdown('**Model V3:** 25% profitability, 20% financial strength, 20% durable growth, 20% cash generation, 15% historical consistency. Annual evidence: at least three fiscal years, five observed KPIs, comparable sector peers (at least five), and ≥70% of dimension weights. Missing dimensions are **not reweighted** upward. Bank/insurer analysis excludes industrial FCF and liquidity measures; their model weights are 35% profitability, 25% financial strength, 25% growth, and 15% consistency. See FUNDAMENTAL_QUALITY_RANKING_WIKI.md. Valuation is independent from quality.')
            from fundamental_rankings_engine import DIMENSION_WEIGHTS, FINANCIAL_DIMENSION_WEIGHTS
            st.dataframe(pd.DataFrame({'Dimension': list(DIMENSION_WEIGHTS), 'Nonfinancial %': [int(100 * v) for v in DIMENSION_WEIGHTS.values()], 'Banks/financials %': [int(100 * FINANCIAL_DIMENSION_WEIGHTS.get(k,0)) for k in DIMENSION_WEIGHTS]}), hide_index=True, use_container_width=True)
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



def _render_india_rankings():
    """Always show imported Indian ratios; keep historical rankings distinct."""
    from pathlib import Path
    token = _snapshot_token()
    with st.spinner('Loading saved India financial data…'):
        df = _load('India', token)
    if df.empty:
        st.error('India financial records are not available in this deployment.')
        st.caption('Expected: data/india_financials/reference_snapshot.csv (or annual company JSON files).')
        candidate = DATA / 'india_financials' / 'reference_snapshot.csv'
        st.code(f'Snapshot exists: {candidate.is_file()} | location: {candidate} | app root: {Path.cwd()}')
        st.info('The previous package includes a 514-company ratio snapshot, but it must be committed under the same repository root as app.py. This page does not download or create financial statements.')
        return

    snap = snapshot_comparison(df)
    ranked = df[df['Status'].eq('Ranked')]
    one_date = snap[snap.get('Financial data type', pd.Series(index=snap.index, dtype=str)).eq('Single-period ratio snapshot')]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Companies with data', f'{len(df):,}')
    m2.metric('Multi-year ranked', f'{len(ranked):,}')
    m3.metric('Snapshot comparisons', f'{snap["Snapshot comparison / 100"].notna().sum():,}')
    m4.metric('Annual statement histories', f'{(pd.to_numeric(df["Years"], errors="coerce") >= 3).sum():,}')

    tab1, tab2, tab3 = st.tabs(['Company financials', 'Verified consistency ranks', 'Intrinsic & Graham'])
    with tab1:
        st.info('Single-date ratio comparison, **not** a multi-year consistency rank. Historical rankings require three consecutive years of actual financial statements.')
        term = st.text_input('Search NSE company', key='india_fundamental_find', placeholder='Symbol or company')
        view = snap
        if term:
            view = view[view['Ticker'].fillna('').str.contains(term, case=False, regex=False)
                        | view['Company'].fillna('').str.contains(term, case=False, regex=False)]
        cols = ['Snapshot position','Ticker','Company','Snapshot comparison / 100',
                'Snapshot metric coverage %','ROE','Debt / equity','Current ratio',
                'Operating margin','Net margin','Revenue growth','Liabilities / assets',
                'P/E','P/B','Source','As of']
        display = view.copy()
        for metric in ['ROE', 'Operating margin', 'Net margin', 'Revenue growth', 'Liabilities / assets']:
            display[metric] = pd.to_numeric(display[metric], errors='coerce') * 100
        config = {
            'Snapshot position': st.column_config.NumberColumn('Snapshot #', format='%d'),
            'Snapshot comparison / 100': st.column_config.ProgressColumn('Snapshot / 100', min_value=0, max_value=100, format='%.1f'),
            'Snapshot metric coverage %': st.column_config.NumberColumn('Coverage', format='%.1f%%'),
            **{metric:st.column_config.NumberColumn(metric,format='%.1f%%') for metric in ['ROE', 'Operating margin', 'Net margin', 'Revenue growth', 'Liabilities / assets']},
        }
        st.dataframe(display[[col for col in cols if col in display.columns]],
                     use_container_width=True, hide_index=True, height=560, column_config=config)
        st.download_button('Export India company ratios', view.drop(columns=['History'], errors='ignore').to_csv(index=False),
                           'india_company_ratios.csv', mime='text/csv', key='india_snapshot_export')
    with tab2:
        if ranked.empty:
            st.warning('No verified India consistency ranks yet. Financial snapshots are available in the first tab, but they do not contain annual ROE, margin, leverage and dividend histories.')
            st.caption('To calculate real consistency scores, save 3–5 consecutive years of annual consolidated financial statements per company to data/india_financials/companies/SYMBOL.json using the documented schema. Merely refreshing current ratios will not establish historical performance.')
        else:
            cols = ['Rank','Ticker','Company','Sector','Fundamental score','Consistency','Years','Metric coverage %','Source']
            st.dataframe(ranked[[col for col in cols if col in ranked]], use_container_width=True, hide_index=True)
    with tab3:
        cols = ['Ticker','Company','Calculated EPS','Book value / share','Graham number',
                'DCF Bear','DCF Base','DCF Bull','FCF observations','Valuation note']
        st.dataframe(df[[col for col in cols if col in df]], use_container_width=True, hide_index=True)
        st.caption('Graham and DCF require underlying statement-derived net income, reported shares and cash-flow history. A single-date financial-ratio export cannot support these calculations.')
    with st.expander('Source & coverage diagnostics'):
        expected = DATA / 'india_financials' / 'reference_snapshot.csv'
        st.write({'snapshot_present': expected.exists(),
                  'snapshot_rows': len(load_india_reference_snapshot()),
                  'annual_histories': int((pd.to_numeric(df['Years'],errors='coerce') >= 3).sum()),
                  'source_types': df['Source'].value_counts().to_dict()})
        st.caption('An NSE 403 or a Yahoo rate limit should not affect this cached page. Verify snapshot files are actually deployed.')
