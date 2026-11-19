"""India Financial KPI Intelligence — NSE/Screener/Yahoo reference data logic.

All network operations happen only when the user explicitly presses Analyze.
Figures retain their original units: Screener statement amounts in INR crore,
Yahoo quote data in INR, and Yahoo cash flows converted to INR crore.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
import math
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from india_financial_data import safe_symbol
from india_valuation_reference import (
    fetch_company, fetch_market_financials, fetch_nse_quote,
    choose_valuation_fields, automatic_assessment, derive_fundamentals,
    aligned_annual, row_series, latest, peer_median_pe, company_url,
)
from research_theme import apply_research_theme, PLOTLY_LAYOUT
from india_financial_ui import _read
from india_screener_statements import prepare_statement

HOLDINGS = Path(__file__).resolve().parent / 'data' / 'india_holdings'


def available(value):
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def money_cr(value):
    """Amounts supplied in INR crore; never divide them by 10 million again."""
    if not available(value):
        return 'N/A'
    value = float(value)
    if abs(value) >= 100000:
        return f'₹{value / 100000:,.2f} lakh Cr'
    return f'₹{value:,.2f} Cr'


def money_inr(value):
    """Full INR per-share / current-price values."""
    return f'₹{float(value):,.2f}' if available(value) else 'N/A'


def number(value, kind='number'):
    if not available(value):
        return 'N/A'
    v = float(value)
    if kind == 'crore':
        return money_cr(v)
    if kind == 'inr':
        return money_inr(v)
    if kind == 'pct':
        return f'{v:,.2f}%'
    if kind == 'shares':
        return f'{v:,.2f} Cr shares'
    if kind == 'ratio':
        return f'{v:,.2f}×'
    return f'{v:,.2f}'


def safe_ratio(a, b, scale=1):
    return float(a) / float(b) * scale if available(a) and available(b) and float(b) != 0 else np.nan


def statement_value(tables, table, patterns):
    return latest(aligned_annual(tables.get(table), patterns))


def load_reference(symbol):
    """Individual provider failures do not suppress other available providers."""
    errors = []
    nse, screener, yahoo = {}, {}, {}
    try:
        nse = fetch_nse_quote(symbol)
    except Exception as exc:
        errors.append(f'NSE quote: {type(exc).__name__}: {str(exc)[:170]}')
    try:
        screener = fetch_company(symbol)
    except Exception as exc:
        errors.append(f'Screener consolidated: {type(exc).__name__}: {str(exc)[:170]}')
    try:
        yahoo = fetch_market_financials(symbol)
    except Exception as exc:
        errors.append(f'Yahoo Finance: {type(exc).__name__}: {str(exc)[:170]}')
    tables = screener.get('tables', {})
    selected, provenance, missing = choose_valuation_fields(
        nse, screener.get('quote_fields', {}), yahoo)
    market = dict(yahoo)
    market['price'] = selected['price']
    market['dividend_pct'] = selected['dividend_pct']
    market['quote_fields'] = {**yahoo.get('quote_fields', {}), **selected}
    assessment = automatic_assessment(tables, market)
    if available(selected['trailing_pe']):
        assessment['pe'] = selected['trailing_pe']
    if available(selected['industry_pe']):
        assessment['industry_pe'] = selected['industry_pe']
    assessment['provenance'] = provenance
    assessment['missing'] = missing
    return {'symbol': symbol, 'nse': nse, 'screener': screener, 'yahoo': yahoo,
            'selected': selected, 'assessment': assessment, 'errors': errors,
            'loaded_utc': datetime.now(timezone.utc).isoformat()}


def tile_group(title, entries):
    st.markdown(f'<div class="ik-section">{escape(title)}</div>', unsafe_allow_html=True)
    for start in range(0, len(entries), 5):
        cols = st.columns(5, gap='small')
        for col, (label, value, kind, source) in zip(cols, entries[start:start+5]):
            col.markdown('<div class="ik-tile" title="' + escape(str(source), quote=True) + '">'
                         '<div class="ik-label">' + escape(label) + '</div>'
                         '<div class="ik-value">' + escape(number(value, kind)) + '</div>'
                         '<div class="ik-source">' + escape(str(source))[:85] + '</div></div>',
                         unsafe_allow_html=True)


def metric_plot(title, items, kind='crore'):
    """items: [(name, pandas Series)] with authentic dated source columns."""
    fig = go.Figure()
    for name, series in items:
        if series is not None and not series.empty:
            clean = pd.to_numeric(series, errors='coerce').dropna()
            if len(clean):
                fig.add_trace(go.Scatter(x=[str(x) for x in clean.index], y=clean.values,
                                         name=name, mode='lines+markers', connectgaps=False))
    if not fig.data:
        st.info(f'{title}: no verified observations supplied.')
        return
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(title=title, height=325, margin=dict(l=35, r=15, t=52, b=45),
                      xaxis_title=None, yaxis_title='₹ crore' if kind=='crore' else kind,
                      legend=dict(orientation='h', y=-0.29), hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)


def series_for(tables, table, patterns):
    return aligned_annual(tables.get(table), patterns)


def _styles():
    apply_research_theme()
    st.markdown('''<style>
    .ik-kicker{font-size:.77rem;letter-spacing:.13em;color:#5dccf6;font-weight:800}
    .ik-section{color:#eff7ff;font-weight:760;font-size:1rem;margin:17px 0 9px}
    .ik-tile{border:1px solid #2a3c55;border-radius:10px;background:#142137;
      min-height:94px;padding:10px 10px;margin-bottom:4px;overflow:hidden}
    .ik-label{font-size:.72rem;color:#b4c9dc;line-height:1.25}
    .ik-value{font-size:1.14rem;white-space:nowrap;color:#f4f8ff;font-weight:760;margin-top:8px}
    .ik-source{font-size:.61rem;color:#7f9bb9;margin-top:7px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    @media(max-width:900px){.ik-value{font-size:.91rem}.ik-tile{padding:8px 5px}}
    </style>''', unsafe_allow_html=True)


def render_india_kpi_intelligence():
    _styles()
    st.markdown('<div class="ik-kicker">INDIA  /  COMPANY FUNDAMENTALS  /  FINANCIAL KPI INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title('🇮🇳 India Company Financial KPI Intelligence')
    st.caption('NSE quotes → Screener consolidated financials → Yahoo fallback, per metric. '
               'Amounts in INR crore · price and EPS in ₹ per share · sources indicated on each tile.')
    directory = _read(HOLDINGS, 'companies.csv')
    symbols = []
    if not directory.empty and 'symbol' in directory:
        for raw in directory['symbol'].dropna().astype(str).unique():
            try:
                symbols.append(safe_symbol(raw.removesuffix('.NS')))
            except ValueError:
                pass
    symbols = sorted(set(symbols))
    with st.form('india_kpi_reference_form'):
        left, middle, right = st.columns([1.3, 1.2, 1], vertical_alignment='bottom')
        typed = left.text_input('NSE ticker', st.session_state.get('india_kpi_reference_symbol', 'MGL')).strip().upper()
        option = middle.selectbox('Or choose an NSE constituent', ['Direct ticker']+symbols)
        submit = right.form_submit_button('Analyze financial KPIs', type='primary', use_container_width=True)
    if submit:
        try:
            symbol = safe_symbol((typed if option == 'Direct ticker' else option).removesuffix('.NS'))
        except ValueError:
            st.error('Enter a valid NSE ticker (MGL, RELIANCE, TCS, etc.).')
            return
        with st.spinner(f'Loading available sources for {symbol}…'):
            result = load_reference(symbol)
        st.session_state['india_kpi_reference_symbol'] = symbol
        st.session_state.setdefault('india_kpi_reference_results', {})[symbol] = result
    symbol = st.session_state.get('india_kpi_reference_symbol')
    cached = st.session_state.get('india_kpi_reference_results', {}).get(symbol)
    if not cached:
        st.info('Choose a company and click Analyze financial KPIs. Live requests are not made during page navigation.')
        return
    tables = cached['screener'].get('tables', {})
    selected = cached['selected']; assessment = cached['assessment']; fundamental = assessment['metrics']
    provenance = assessment['provenance']; quote = cached['yahoo'].get('quote_fields', {})
    if not tables and not any(available(v) for v in selected.values()):
        st.warning('No financial data was returned by the accessible sources. See Sources & diagnostics.')
    st.markdown(f'### {escape(symbol)} · Financial Overview')
    st.caption('Data fetched ' + cached['loaded_utc'][:16].replace('T', ' ') + ' UTC · '
               'Financial statement values come from consolidated Screener tables when accessible; '
               'market ratios/quotes are selected independently by source.')
    tabs = st.tabs(['Overview', 'Growth & Margins', 'Balance Sheet', 'Cash Flow',
                    'Value & Intrinsic', 'Annual / Quarterly Trends', 'Sources & Diagnostics'])
    def entry(label, key, kind='number'):
        return (label, selected.get(key), kind, provenance.get(key, 'N/A'))
    sales=fundamental['sales_cr']; net=fundamental['net_profit_cr']; eps=fundamental['eps_inr']
    assets=statement_value(tables, 'Balance Sheet', [r'^Total Assets'])
    borrow=statement_value(tables, 'Balance Sheet', [r'^Borrowings\s*\+?$'])
    cash=statement_value(tables, 'Balance Sheet', [r'^Cash Equivalents', r'^Cash & Cash Equivalents', r'^Cash and Cash Equivalents'])
    reserves=statement_value(tables, 'Balance Sheet', [r'^Reserves\s*\+?$'])
    equitycapital=fundamental.get('equity_capital_cr', np.nan)
    equity=(equitycapital+reserves) if available(equitycapital) and available(reserves) else np.nan
    if not available(equity):
        equity=statement_value(tables, 'Balance Sheet', [r'^Total Equity$', r'^Shareholders.? Equity$'])
    liabilities=assets-equity if available(assets) and available(equity) else np.nan
    op_profit=statement_value(tables, 'Profit & Loss', [r'^Operating Profit\s*\+?$'])
    raw_cfo=fundamental['cfo_cr']; fcf=fundamental['fcf_proxy_cr']; capex=fundamental['capex_cr']
    with tabs[0]:
        tile_group('Performance', [
            ('Revenue',sales,'crore','Screener · latest annual consolidated'),
            ('Net profit',net,'crore','Screener · latest annual consolidated'),
            ('EPS',eps,'inr','Screener · reported EPS'),
            ('Operating margin',safe_ratio(op_profit,sales,100),'pct','Screener · operating profit / sales'),
            ('Net margin',safe_ratio(net,sales,100),'pct','Screener · net profit / sales'),
            ('Revenue CAGR · 5Y',fundamental['revenue_cagr_5y_pct'],'pct','Screener · historical'),
            ('EPS CAGR · 5Y',fundamental['eps_cagr_5y_pct'],'pct','Screener · historical'),
            ('Cash from operations',raw_cfo,'crore','Screener · annual'),
            ('FCF proxy',fcf,'crore','Screener · CFO minus verified capex'),
            ('Market price',selected['price'],'inr',provenance.get('price','N/A'))])
        tile_group('Market snapshot', [entry('Market capitalization','market_cap_cr','crore'),
                                       entry('P/E','trailing_pe','ratio'),entry('P/B','price_to_book','ratio'),
                                       entry('Dividend yield','dividend_pct','pct'), entry('ROE','roe_pct','pct')])
    with tabs[1]:
        tile_group('Growth', [('Revenue CAGR · 5Y',fundamental['revenue_cagr_5y_pct'],'pct','Screener · annual'),
                              ('Net profit CAGR · 5Y',fundamental['profit_cagr_5y_pct'],'pct','Screener · annual'),
                              ('EPS CAGR · 5Y',fundamental['eps_cagr_5y_pct'],'pct','Screener · annual'),
                              entry('Revenue growth · quote','revenue_growth_pct','pct')])
        tile_group('Profitability', [('Operating margin',safe_ratio(op_profit,sales,100),'pct','Reported consolidated P&L'),
                                     ('Net margin',safe_ratio(net,sales,100),'pct','Reported consolidated P&L'),
                                     ('FCF proxy margin',safe_ratio(fcf,sales,100),'pct','CFO minus identifiable capex / sales'),
                                     entry('ROE · quote','roe_pct','pct'), entry('ROCE · quote','roce_pct','pct')])
    with tabs[2]:
        tile_group('Assets, equity & borrowing', [('Total assets',assets,'crore','Screener · consolidated balance sheet'),
            ('Total liabilities · derived',liabilities,'crore','Only if assets and equity available'),
            ('Equity · capital + reserves',equity,'crore','Screener · balance sheet; not adjusted for minority interests'),
            ('Borrowings',borrow,'crore','Screener · reported borrowings'),
            ('Cash equivalents',cash,'crore','Screener · if separately disclosed'),
            ('Borrowings less cash',borrow-cash if available(borrow) and available(cash) else np.nan,'crore','Not full net debt'),
            ('Borrowings / equity',safe_ratio(borrow,equity),'ratio','Not appropriate for all financial institutions')])
        st.caption('Screener balance-sheet categories may include noncontrolling interests, leases or other claims. '
                   'Derived liabilities/equity are indicative and should be verified against company filings.')
    with tabs[3]:
        tile_group('Cash generation', [('Operating cash flow',raw_cfo,'crore','Screener · cash flows'),
             ('Identified capital expenditure',capex,'crore','Only a dedicated identifiable capex line'),
             ('Free cash flow proxy',fcf,'crore','CFO less capex; not verified FCFE'),
             ('CFO / net profit',safe_ratio(raw_cfo,net),'ratio','Cash conversion proxy'),
             ('FCF / net profit',safe_ratio(fcf,net),'ratio','Cash conversion after verified capex'),
             ('Normalized FCF proxy',assessment['normalized_fcf_cr'],'crore','Yahoo · mean up to 5 annual observations')])
        st.caption('If Screener does not separately disclose capital expenditure, FCF proxy remains N/A. '
                   'Yahoo cash-flow history has its own reporting scope and date; do not merge it into Screener rows silently.')
    with tabs[4]:
        tile_group('Market multiples & peer context', [entry('Share price','price','inr'),
             entry('Trailing P/E','trailing_pe','ratio'),entry('Industry / peer P/E','industry_pe','ratio'),
             entry('Forward P/E','forward_pe','ratio'), entry('P/B','price_to_book','ratio'),
             entry('EV / EBITDA','ev_ebitda','ratio'), entry('Price / Sales','price_to_sales','ratio'),
             ('PEG · historical',assessment['peg'],'ratio','Historical EPS CAGR; not forecast'),
             ('PEGY · historical',assessment['pegy'],'ratio','Historical EPS CAGR + dividend yield')])
        bvps=safe_ratio(equity,assessment['shares_cr'])
        graham=math.sqrt(22.5*eps*bvps) if all(available(v) and float(v)>0 for v in (eps,bvps)) else np.nan
        tile_group('Asset & Graham reference', [('Book value / share · proxy',bvps,'inr',
             'Screener equity estimate / Yahoo current shares; different dates may apply'),
             ('Graham Number · provisional',graham,'inr','√(22.5 × positive EPS × positive book value/share)'),
             ('Net current asset value/share',np.nan,'inr','Requires verified current assets, all liabilities and preferred claims')])
        st.markdown('#### Five-year provisional DCF · original reference assumptions')
        scenarios=assessment['scenarios'].copy()
        st.dataframe(scenarios.style.format({'Intrinsic Value ₹':money_inr,'Margin of Safety %':lambda v:number(v,'pct'),
                    'Buy Price @ 25% MOS ₹':money_inr}),use_container_width=True,hide_index=True)
        st.caption('The source project uses normalized annual Yahoo CFO − capex as an FCFE proxy. '
                   'This is not validated FCFE or FCFF, and bank/NBFC valuations need different methods. '
                   'DCF values require at least three comparable annual FCF observations and share count.')
    with tabs[5]:
        freq=st.radio('Reporting frequency', ['Annual', 'Quarterly'],horizontal=True,key='india_kpi_reference_frequency')
        if freq=='Annual':
            sales_hist=series_for(tables,'Profit & Loss',[r'^Sales\s*\+?$',r'^Revenue'])
            profit_hist=series_for(tables,'Profit & Loss',[r'^Net Profit\s*\+?$'])
            op_hist=series_for(tables,'Profit & Loss',[r'^Operating Profit\s*\+?$'])
            cfo_hist=series_for(tables,'Cash Flows',[r'^Cash from Operating Activit'])
            borrow_hist=series_for(tables,'Balance Sheet',[r'^Borrowings\s*\+?$'])
            st.caption('Screener annual consolidated values shown in ₹ crore; periods are source-labelled.')
            a,b=st.columns(2)
            with a: metric_plot('Revenue & earnings', [('Sales',sales_hist),('Net profit',profit_hist),('Operating profit',op_hist)])
            with b: metric_plot('Operating cash flow & borrowings',[('Cash from operations',cfo_hist),('Borrowings',borrow_hist)])
        else:
            quarters=tables.get('Quarterly Results')
            st.caption('Quarterly figures from Screener consolidated results if accessible. '
                       'No annual totals are reclassified as individual quarters.')
            q_sales=row_series(quarters,[r'^Sales\s*\+?$',r'^Revenue'])
            q_profit=row_series(quarters,[r'^Net Profit\s*\+?$'])
            q_op=row_series(quarters,[r'^Operating Profit\s*\+?$'])
            metric_plot('Quarterly sales & earnings',[('Sales',q_sales),('Net profit',q_profit),('Operating profit',q_op)])
        st.caption('No missing reporting periods are replaced with zero. Cash flows and balance-sheet values are annual unless explicit quarterly values are provided.')
    with tabs[6]:
        st.markdown('#### Metric provenance')
        st.dataframe(pd.DataFrame([{'Metric': k.replace('_',' ').title(),
            'Value':number(v,'crore' if k=='market_cap_cr' else 'number'),
            'Provider':provenance.get(k,'N/A'), 'Status':assessment['missing'].get(k,'Available')}
            for k,v in selected.items()]),use_container_width=True,hide_index=True)
        st.markdown('#### Provider status')
        for source, ok in [('NSE quote',bool(cached['nse'])),
                           ('Screener consolidated',bool(tables)),('Yahoo market financials',bool(cached['yahoo']))]:
            st.write(('✅ ' if ok else '⚠️ ')+source)
        for error in cached['errors']:
            st.caption(error)
        st.link_button('↗ Screener consolidated financial statements',company_url(symbol))
        st.link_button('↗ Yahoo .NS financials',f'https://finance.yahoo.com/quote/{symbol}.NS/financials/')
        st.caption('Provider access and data terms apply. No bypass of website restrictions. '
                   'This page is a reference-style KPI viewer; differences in consolidated/standalone scope and fiscal dates are not reconciled automatically.')


    # The original consolidated Screener statements appear at the bottom of
    # India Company Financial KPI Intelligence, without any additional request.
    st.divider()
    st.markdown('### 📑 Consolidated Balance Sheet & Cash Flow')
    st.caption('Source: Screener.in · reported consolidated figures · ₹ crore unless the original row specifies otherwise. '
               'Historical periods are chronological; missing entries are N/A. No figures are inferred or mixed with Yahoo.')
    period_choice = st.segmented_control(
        'Historical periods', ['5 years', '8 years', '12 years', 'All available'],
        default='8 years', key='india_kpi_screener_statement_periods')
    count = {'5 years': 5, '8 years': 8, '12 years': 12, 'All available': 0}.get(period_choice, 8)
    for source_key, heading in [('Balance Sheet', 'Balance Sheet'), ('Cash Flows', 'Cash Flow Statement')]:
        st.markdown(f'#### {heading}')
        report = prepare_statement(tables.get(source_key), periods=count)
        if report.empty:
            st.info(f'{heading} is unavailable from Screener for {symbol}. '
                    'Other available KPI values are preserved; this section does not invent financial statements.')
        else:
            st.dataframe(report, use_container_width=True, hide_index=True,
                         height=min(540, max(185, 38 * (len(report) + 1))))
            st.download_button(
                f'Download {heading} CSV',
                data=report.to_csv(index=False).encode('utf-8-sig'),
                file_name=f'{symbol}_screener_{source_key.lower().replace(" ", "_")}.csv',
                mime='text/csv', key=f'india_kpi_{source_key}_csv')
    if cached['screener'].get('retrieved_utc'):
        st.caption('Screener retrieved (UTC): ' + str(cached['screener']['retrieved_utc'])[:19].replace('T', ' '))
    st.link_button('↗ View original consolidated statements on Screener', company_url(symbol))
    st.caption('These are the source-reported statements for reference, not independently audited by this dashboard. '
               'Please verify important decisions against company filings and applicable source usage terms.')
