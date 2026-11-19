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
from india_screener_statements import prepare_statement, prepare_source_table
from india_screener_trends import render_screener_trends

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


def render_india_revenue_sankey(tables):
    """Only reconcile one published annual P&L period. Residual is explicitly labelled."""
    sales = aligned_annual(tables.get('Profit & Loss'), [r'^Sales\s*\+?$', r'^Revenue\s*\+?$'])
    profit = aligned_annual(tables.get('Profit & Loss'), [r'^Net Profit\s*\+?$', r'^Net Profit After Tax$', r'^Profit After Tax$'])
    operating = aligned_annual(tables.get('Profit & Loss'), [r'^Operating Profit\s*\+?$'])
    common = [date for date in sales.index if date in profit.index]
    common = [date for date in common if available(sales[date]) and available(profit[date])]
    if not common:
        st.info('Revenue-to-net-income flow unavailable: no aligned annual revenue and net profit.')
        return
    date = common[-1]
    revenue, net = float(sales[date]), float(profit[date])
    if not (revenue > 0 and 0 <= net <= revenue):
        st.info('Net loss or non-reconciling financials: review the income statement; no false Sankey flows are drawn.')
        return
    if date in operating.index and available(operating[date]) and net <= float(operating[date]) <= revenue:
        op = float(operating[date])
        names = ['Revenue', 'Operating costs & adjustments (residual)', 'Operating profit',
                 'Other items & taxes (residual)', 'Net profit']
        src, dst, vals = [0,0,2,2], [1,2,3,4], [revenue-op,op,op-net,net]
    else:
        names = ['Revenue','Costs, taxes & adjustments (residual)','Net profit']
        src, dst, vals = [0,0], [1,2], [revenue-net,net]
    fig = go.Figure(go.Sankey(arrangement='snap',
       node=dict(label=names, pad=24, thickness=18,
                 color=['#2e82b7' if n in ('Revenue','Operating profit') else '#25a77e' if n == 'Net profit' else '#b86a79' for n in names]),
       link=dict(source=src,target=dst,value=vals,color='rgba(81,183,232,.32)')))
    fig.update_layout(title=f'Revenue → Net Profit · {date} · ₹ crore',
        paper_bgcolor='#142137',plot_bgcolor='#142137',font=dict(color='#e7eef9'),
        height=390,margin=dict(l=15,r=15,t=55,b=15))
    st.plotly_chart(fig,use_container_width=True)
    st.caption('Residuals are mathematical differences from reported totals, not independently reported expense categories.')


def render_nse_peer_fallback(symbol):
    """Constituent peer context when Screener does not publish an accessible peer table.

    A shared NSE sector index is *not* Screener's published peer set.
    """
    membership = _read(HOLDINGS, 'constituents.csv')
    if membership.empty or not {'symbol','category','index_name','company_key'}.issubset(membership):
        st.info('No Screener peer table was available and no saved NSE peer memberships were found.')
        return
    matched = membership[(membership['symbol'].str.upper() == symbol) &
        membership['category'].isin(['Sector','Thematic'])]
    if matched.empty:
        st.info('Screener peer data is unavailable. This security has no matching saved NSE sector/thematic index.')
        return
    same = membership[(membership['index_name'].isin(set(matched['index_name']))) &
        (membership['category'].isin(['Sector','Thematic']))].drop_duplicates('company_key')
    cached_financials = _read(Path(__file__).resolve().parent/'data'/'india_financials',
                              'company_financial_summary.csv')
    fields=['company_key','symbol','company_name']
    view=same[fields].copy()
    view.columns=['company_key','Symbol','Company']
    if not cached_financials.empty and 'company_key' in cached_financials:
        cols=['company_key']+[k for k in ['pe','pb','market_cap','roe','revenue_yoy','retrieved_utc'] if k in cached_financials]
        view=view.merge(cached_financials[cols].drop_duplicates('company_key'),on='company_key',how='left')
    view=view.drop(columns=['company_key']).sort_values('Symbol')
    st.warning('Screener peer comparison was not included in the accessible response. '
               'Displaying **alternative NSE shared-sector constituents**, not Screener peer rankings.')
    st.caption('Shared NSE indices: '+', '.join(sorted(matched['index_name'].unique())))
    st.dataframe(view, use_container_width=True, hide_index=True, height=380)
    st.download_button('Export NSE shared-sector context', view.to_csv(index=False).encode('utf-8'),
                       file_name=f'{symbol}_nse_shared_sector_context.csv',mime='text/csv')


def render_india_sources(cached, tables, selected, provenance, symbol):
    """Show actual provider coverage without mistaking HTTP success for usable financial data."""
    st.markdown('#### Source coverage and retrieval diagnostics')
    name_map = [('NSE quote', cached.get('nse', {})), ('Screener consolidated', cached.get('screener', {})),
                ('Yahoo market financials', cached.get('yahoo', {}))]
    results=[]
    for name, response in name_map:
        fields = response.get('quote_fields', {}) if isinstance(response,dict) else {}
        is_screener=name.startswith('Screener')
        n_tables=len(tables) if is_screener else 0
        numeric=sum(available(v) for v in fields.values()) if isinstance(fields,dict) else 0
        results.append({'Provider':name,'Response received':bool(response),
                        'Statement tables':n_tables,'Usable numeric quote fields':numeric,
                        'Status':'Usable data' if (n_tables or numeric) else 'Missing / unverified'})
    st.dataframe(pd.DataFrame(results),use_container_width=True,hide_index=True)
    st.markdown('#### Consolidated statement availability')
    expected=['Quarterly Results','Profit & Loss','Balance Sheet','Cash Flows','Ratios','Shareholding Pattern','Peer Comparison']
    st.dataframe(pd.DataFrame([{'Table':name,'Available':isinstance(tables.get(name),pd.DataFrame) and not tables[name].empty,
            'Rows':len(tables[name]) if isinstance(tables.get(name),pd.DataFrame) else 0}
            for name in expected]),use_container_width=True,hide_index=True)
    st.markdown('#### Metric sources')
    st.dataframe(pd.DataFrame([{'Metric':key.replace('_',' ').title(),'Value':number(v,'crore' if key=='market_cap_cr' else 'number'),
        'Selected source':provenance.get(key,'Unknown')} for key,v in selected.items()]),use_container_width=True,hide_index=True)
    if cached.get('errors'):
        with st.expander(f"Provider errors ({len(cached['errors'])})",expanded=False):
            for error in cached['errors']:
                st.warning(error)
    else:
        st.success('No provider exceptions were recorded. Missing tables may still reflect restricted or incomplete source data.')
    st.caption('Financial statements and market prices can have different dates and scopes. Source availability does not guarantee complete coverage.')
    st.link_button('↗ Screener consolidated report',company_url(symbol))
    st.link_button('↗ Yahoo financials',f'https://finance.yahoo.com/quote/{symbol}.NS/financials/')


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
    st.caption('NSE · Screener consolidated · Yahoo  |  INR crore unless noted')
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
        st.markdown('#### Revenue → Net Income')
        render_india_revenue_sankey(tables)
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
        render_screener_trends(tables)
    with tabs[6]:
        render_india_sources(cached,tables,selected,provenance,symbol)


    # All Screener tables are taken from the same previously fetched
    # consolidated response. No extra requests when switching sections.
    st.divider()
    st.markdown('### 📑 Screener · Consolidated Financial Statements & Ownership')
    st.caption('Source: Screener.in · consolidated where available. Financial statement amounts '
               'are generally ₹ crore; quarterly EPS, percentages, peer prices and ownership '
               'figures retain their original source units. No synthetic data.')
    categories = [
        ('Peer Comparison', 'Peer Comparison', False),
        ('Quarterly Results', 'Quarterly Results', True),
        ('Profit & Loss', 'Profit & Loss', True),
        ('Balance Sheet', 'Balance Sheet', True),
        ('Cash Flows', 'Cash Flow', True),
        ('Ratios', 'Financial Ratios & Efficiency', True),
        ('Shareholding Pattern', 'Shareholding Pattern', False),
    ]
    # Additional yearly shareholding tables are included if published.
    categories.extend((k, k, False) for k in tables
                      if k.startswith('Shareholding Pattern ('))
    available_count = sum(1 for key, _, _ in categories
                          if isinstance(tables.get(key), pd.DataFrame)
                          and not tables[key].empty)
    st.caption(f'{available_count} of {len(categories)} published tables available from this fetch.')
    period_choice = st.selectbox(
        'History window', ['5 periods', '8 periods', '12 periods', 'All available'],
        index=1, key='india_kpi_screener_table_periods')
    count = {'5 periods': 5, '8 periods': 8, '12 periods': 12,
             'All available': 0}[period_choice]
    table_tabs = st.tabs([label for _, label, _ in categories])
    for tab, (source_key, label, is_financial) in zip(table_tabs, categories):
        with tab:
            raw = tables.get(source_key)
            # Each quarterly/annual financial table has reporting-period headings.
            # Peer tables have company rows and mixed units; ownership tables have %.
            report = prepare_source_table(raw, periods=count, financial=is_financial)
            if report.empty:
                if source_key == 'Peer Comparison':
                    render_nse_peer_fallback(symbol)
                else:
                    st.info(f'{label} is not available in the accessible consolidated '
                            'Screener response for this company. This does not imply zero.')
            else:
                if is_financial:
                    st.caption('Reported period columns · ₹ crore except per-share or % rows.')
                elif source_key == 'Peer Comparison':
                    st.caption('Published peer comparison · mixed units as labelled by Screener.')
                else:
                    st.caption('Published shareholding percentages / shareholder counts · source units.')
                st.dataframe(report, use_container_width=True, hide_index=True,
                             height=min(560, max(220, 36 * (len(report) + 1))))
                st.download_button(
                    f'Export {label} · CSV', report.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f'{symbol}_screener_{re.sub(r"[^a-z0-9]+", "_", source_key.lower()).strip("_")}.csv',
                    mime='text/csv', key=f'india_kpi_screener_export_{source_key}')
    if cached['screener'].get('retrieved_utc'):
        st.caption('Retrieved (UTC): ' + str(cached['screener']['retrieved_utc'])[:19].replace('T', ' '))
    st.link_button('↗ Open Screener consolidated source', company_url(symbol))
    st.caption('Table availability depends on published content and permitted provider access; '
               'peer tables can be loaded dynamically by the source and therefore may be absent. '
               'Verify figures against official company filings and source usage terms.')
