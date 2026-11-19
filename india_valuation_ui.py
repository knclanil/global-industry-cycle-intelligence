"""India Fundamental Valuation — source-traceable, opt-in single-company research.

Inspired by user-attached Factor Holdings Intelligence / india_valuation.py.
Uses the existing verified NSE company directory and saved/on-demand Yahoo snapshots.
Screener is an independent consolidated-statements research link (no scraping).
"""
from __future__ import annotations
from html import escape
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from india_financial_data import DATA, company_file, safe_symbol, screener_url, statement_coverage, liquidation_proxy
from india_financial_ui import _read, _snapshot, _mtime, _fetch_live_company, _style, _header, _fmt
from india_valuation_engine import scenario_table, valuation_metrics, earnings_valuation, numeric, SCENARIOS

ROOT = Path(__file__).resolve().parent
HOLDINGS = ROOT / 'data' / 'india_holdings'


def _tile(label, value, fmt='price', currency='INR'):
    st.metric(label, _fmt(value, fmt, currency))


def render_india_valuation():
    _style()
    _header('INDIA · COMPANY RESEARCH', 'India Fundamental Valuation',
            'NSE-verified securities · Yahoo financial snapshots · Screener consolidated reference · scenario-based values')
    cdf = _read(HOLDINGS, 'companies.csv')
    directory = {}
    if not cdf.empty and {'symbol','company_key','company_name'}.issubset(cdf.columns):
        directory = {str(row['company_key']): dict(row) for _,row in cdf.drop_duplicates('company_key').iterrows()}
    col1, col2, col3 = st.columns([2.7, 1.2, 1.1])
    mode = col2.selectbox('Lookup', ['Direct NSE ticker', 'Holdings directory'] if directory else ['Direct NSE ticker'], key='iv_lookup')
    if mode == 'Holdings directory':
        key = col1.selectbox('Company', list(directory), format_func=lambda k: f"{directory[k]['symbol']} · {directory[k]['company_name']}", key='iv_directory')
        company = directory[key]
        symbol = safe_symbol(company['symbol'])
    else:
        symbol_input = col1.text_input('Company NSE ticker', value=st.session_state.get('india_valuation_symbol', 'MGL'), key='iv_symbol').strip().upper()
        try:
            symbol = safe_symbol(symbol_input.removesuffix('.NS'))
        except ValueError as exc:
            st.error(str(exc)); return
        company = next((c for c in directory.values() if c['symbol'].upper() == symbol),
                       {'symbol': symbol, 'company_key': f'TICKER:{symbol}', 'company_name': symbol, 'isin': '', 'industry': ''})
        key = company['company_key']
    diskfile = company_file(key)
    disk = _snapshot(str(diskfile), _mtime(diskfile))
    if disk and (disk.get('company_key') != key or disk.get('symbol') != symbol):
        disk = {}
    live = st.session_state.setdefault('iv_live_payloads', {}).get(key, {})
    payload = live or disk
    with col3:
        clicked = st.button('Fetch Yahoo financials', type='primary', use_container_width=True, key='iv_fetch')
    if clicked:
        with st.spinner(f'Loading {symbol}.NS financial statements…'):
            try:
                count = st.session_state.get('iv_nonce', 0) + 1
                st.session_state.iv_nonce = count
                new = _fetch_live_company(key, symbol, company['company_name'], company.get('isin', ''), company.get('industry',''), count)
                coverage = statement_coverage(new, 'annual')
                if not coverage['best_periods']:
                    st.warning('Yahoo returned no usable annual core data; prior saved snapshot retained if available.')
                else:
                    st.session_state.iv_live_payloads[key] = new
                    payload = new
                    st.success(f"Yahoo statement data loaded for {symbol}.NS; {len(coverage['best_periods'])} usable annual periods.")
            except Exception as exc:
                st.error(f"Yahoo fetch error: {type(exc).__name__}: {str(exc)[:240]}")
    a,b,c = st.columns(3)
    a.link_button('Screener consolidated ↗', screener_url(symbol), use_container_width=True)
    b.link_button('Yahoo financial statements ↗', f'https://finance.yahoo.com/quote/{symbol}.NS/financials/', use_container_width=True)
    c.link_button('NSE company quote ↗', f'https://www.nseindia.com/get-quotes/equity?symbol={symbol}', use_container_width=True)
    if not payload:
        st.info('No saved financial snapshot found. Choose **Fetch Yahoo financials**, or run the India financial-data GitHub workflow. No entire-universe refresh is needed for this company.')
        return
    if payload.get('company_key') != key or payload.get('symbol') != symbol:
        st.error('Financial snapshot company identifier mismatch.'); return
    coverage = statement_coverage(payload, 'annual')
    periods = coverage['best_periods']
    if not periods:
        st.error('No valid annual financial records are available. A successful provider response alone is not enough to calculate valuations.')
        with st.expander('Provider errors / coverage'):
            st.json({'coverage': coverage, 'notes': payload.get('source_notes', [])})
        return
    period = st.selectbox('Annual fiscal period', periods, key='iv_period')
    val = valuation_metrics(payload, period)
    report = val['report']
    m = report['metrics']
    curr = str(payload.get('currency') or '').upper()
    quote_curr = str((payload.get('quote') or {}).get('currency') or '').upper()
    st.markdown(f"### {escape(payload.get('company_name') or company['company_name'])} · {escape(symbol)}")
    st.caption(f"NSE symbol {symbol} · ISIN {company.get('isin') or payload.get('isin') or 'N/A'} · Annual period {period} · "
               f"Statement currency {curr or 'unknown'} · Quote currency {quote_curr or 'unknown'} · "
               f"Snapshot {payload.get('retrieved_utc') or 'N/A'}")
    industry = (str(company.get('industry') or '') + ' ' + str(payload.get('sector') or '')).lower()
    financial_company = any(x in industry for x in ('bank', 'insurance', 'financial service', 'nbfc', 'lending', 'credit'))
    if financial_company:
        st.warning('Bank/insurer/NBFC: ordinary-company free-cash-flow DCF and debt multiples are not reliable valuation methods. Treat asset and earnings measures cautiously and consult specialized disclosures.')
    if curr != quote_curr or not curr:
        st.warning('Statement and quote currencies are missing or different. Price-based comparisons and margins of safety are disabled until consistent currency is confirmed.')
    tabs = st.tabs(['Valuation Dashboard', 'DCF Scenarios', 'Earnings & Graham', 'Asset & Liquidation', 'Sources & Diagnostics'])
    with tabs[0]:
        cols = st.columns(5)
        for col, (label, value, typ) in zip(cols, [
            ('Market price', val['price'], 'price'), ('Graham Number', val['graham_number'],'price'),
            ('Book / share',val['book_value_per_share'],'price'), ('P/E',val['pe'],'ratio'),
            ('Free cash flow yield',val['fcf_yield'],'pct')]):
            with col: _tile(label, value if label != 'Market price' or curr == quote_curr else None,typ, curr or 'INR')
        table = scenario_table(payload, period=period)
        c1,c2,c3 = st.columns(3)
        for col, row in zip((c1,c2,c3),table['rows']):
            with col:
                st.metric(row['Scenario'] + ' · provisional DCF / share', _fmt(row['Value / share'], 'price', curr or 'INR'))
                st.caption('Margin of safety: ' + (f"{row['Margin of safety %']:.1f}%" if row['Margin of safety %'] is not None else 'N/A'))
        df = pd.DataFrame(table['rows'])
        if df['Value / share'].notna().any():
            fig = go.Figure()
            fig.add_bar(x=df['Scenario'], y=df['Value / share'], marker_color=['#fca5a5','#51b7e8','#34d399'])
            fig.update_layout(title='Five-year DCF scenarios · indicative value per share',
                              paper_bgcolor='#142137',plot_bgcolor='#142137',font_color='#e7eef9',
                              margin=dict(l=20,r=20,t=55,b=20),height=280,yaxis_title=f'{curr or "Reporting currency"} / share')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('DCF N/A: requires at least three consecutive annual free cash-flow periods, positive normalized free cash flow, and a verified share count.')
    with tabs[1]:
        st.markdown('#### Five-year cash-flow DCF · Bear / Base / Bull')
        st.caption('Defaults follow the attached Factor Holdings Intelligence reference: Bear 0% / 12% / 2%; Base 3% / 11% / 3%; Bull 5% / 10% / 3.5% (FCF growth / required return / terminal growth).')
        custom = {}
        with st.expander('Edit scenario assumptions', expanded=False):
            for name, settings in SCENARIOS.items():
                p,q,r=st.columns(3)
                custom[name] = {
                    'growth': p.number_input(f'{name}: FCF growth %',-25.0,40.0,float(settings['growth']),key=f'iv_{name}_growth'),
                    'discount': q.number_input(f'{name}: Required return %',1.0,50.0,float(settings['discount']),key=f'iv_{name}_discount'),
                    'terminal': r.number_input(f'{name}: Terminal growth %',-5.0,12.0,float(settings['terminal']),key=f'iv_{name}_terminal'),
                }
        table = scenario_table(payload, custom, period)
        st.dataframe(pd.DataFrame(table['rows']).set_index('Scenario'), use_container_width=True)
        st.caption(f"Normalized FCF: {_fmt(table['normalized_fcf'], 'money', curr or 'INR')} · {table['fcf_years']} annual periods with FCF · Share count basis: {m.get('share_basis','unknown')}.")
        st.warning('Illustrative proxy only: CFO − capex is NOT validated FCFE or FCFF. These values are not a proven acquisition price or an investment recommendation. Historical FCF can be volatile.')
        with st.expander('Annual cash-flow observations used'):
            st.dataframe(pd.DataFrame(table['fcf_samples'], columns=['Fiscal period','Free cash flow']).set_index('Fiscal period'), use_container_width=True)
    with tabs[2]:
        a,b,c,d = st.columns(4)
        with a: _tile('Graham Number',val['graham_number'],'price',curr or 'INR')
        with b: _tile('Diluted EPS',m.get('diluted_eps'),'price',curr or 'INR')
        with c: _tile('Book value / share',val['book_value_per_share'],'price',curr or 'INR')
        with d: st.metric('EPS 5Y CAGR', f"{val['eps_cagr_5y_pct']:.1f}%" if val['eps_cagr_5y_pct'] is not None else 'N/A')
        st.caption('Graham Number = √(22.5 × positive EPS × positive common book value per share). A screening heuristic, not an intrinsic value guarantee.')
        a,b,c = st.columns(3)
        with a: _tile('P/E',val['pe'],'ratio',curr or 'INR')
        with b: _tile('PEG (5Y historical)',val['peg'],'ratio',curr or 'INR')
        with c: _tile('PEGY (if yield available)',val['pegy'],'ratio',curr or 'INR')
        st.markdown('#### Earnings multiple valuation · illustrative')
        target_pe = st.number_input('Assumed sustainable P/E multiple',min_value=1.0,max_value=50.0,value=15.0,step=0.5,key='iv_target_pe')
        eprice = earnings_valuation(m.get('diluted_eps'),target_pe)
        st.metric('Current EPS × assumed P/E',_fmt(eprice,'price',curr or 'INR'))
        st.caption('This is a multiple-based reference, not an earnings forecast. Compare with appropriate peers and normalized earnings. No peer median is invented.')
    with tabs[3]:
        cols = st.columns(4)
        for col,(name,k) in zip(cols, [('Book / share','book_value_per_share'),('Tangible book / share','tangible_book_per_share'),('Net current asset / share','ncav_per_share'),('Graham Number','graham_number')]):
            with col: _tile(name,val.get(k),'price',curr or 'INR')
        st.caption('Book value uses reported common shareholder equity. Unknown preferred claims and missing goodwill/intangibles remain N/A.')
        a,b=st.columns(2)
        recovery=a.slider('Non-cash asset recovery %',0,100,55,5,key='iv_recovery')
        costs=b.slider('Liquidation expenses % of proceeds',0,25,5,1,key='iv_costs')
        no_preferred=st.checkbox('Assume no preferred claims (scenario only; not verified)',value=False,key='iv_no_pref')
        li=val['liquidation_inputs']
        pref=li.get('preferred_equity')
        if pref is None and no_preferred:
            pref=0
        liquid=liquidation_proxy(li.get('total_assets'),li.get('cash'),li.get('total_liabilities'),li.get('shares_outstanding'),recovery,costs,pref)
        st.metric('Hypothetical liquidation recovery / common share',_fmt(liquid,'price',curr or 'INR'))
        st.caption('A liquidation model assumes proceeds from disposals, settlement of ALL liabilities and claims, and costs. This is not an appraisal or a predicted payout.')
    with tabs[4]:
        provenance = pd.DataFrame([
            {'Metric':'Index identity and memberships','Source':'NSE saved constituent lists','As of': 'See India holdings snapshots'},
            {'Metric':'Annual income / balance / cash flow','Source':'Yahoo Finance snapshot','As of':payload.get('retrieved_utc','N/A')},
            {'Metric':'Current market price and shares','Source':'Yahoo Finance quote snapshot','As of':(payload.get('quote') or {}).get('asof_utc','N/A')},
            {'Metric':'Screener consolidated statements','Source':'External company reference only — not automatically imported','As of':'N/A'},
            {'Metric':'Graham / DCF / liquidation','Source':'Derived model assumptions + disclosed inputs','As of':period},
        ])
        st.dataframe(provenance,hide_index=True,use_container_width=True)
        st.json({'coverage':coverage,'source_periods':report['source_periods'],
                 'statement_currency':curr or 'unknown','quote_currency':quote_curr or 'unknown',
                 'share_count_basis':m.get('share_basis'),'source_notes':payload.get('source_notes',[])})
        st.info('NSE/Screener per-field quote fallback from the original reference project is not silently merged here. Market multiples and financial statements must have compatible dates and accounting scope before combining sources.')
