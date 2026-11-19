"""Read-only professional India financial research and sector/factor analytics.

NSE = verified constituents. Yahoo Finance = optional cached financial snapshots.
Screener = independent consolidated-report link; not scraped/reproduced.
No rankings, inferred index weights, or synchronous financial API calls.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import json
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from india_financial_data import (
    AGGREGATE_FIELDS, DATA, MONEY_METRICS, PERCENT_KPIS, RATIO_KPIS, build_kpis,
    company_file, equity_dcf_proxy, liquidation_proxy, load_company,
    safe_symbol, screener_url,
)
from research_theme import PLOTLY_LAYOUT, apply_research_theme

BASE = Path(__file__).resolve().parent
HOLDINGS = BASE / 'data' / 'india_holdings'


def _mtime(path: Path) -> int:
    return path.stat().st_mtime_ns if path.exists() else 0


@st.cache_data(show_spinner=False, max_entries=22)
def _csv(path: str, mtime_ns: int) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _read(directory: Path, filename: str) -> pd.DataFrame:
    path = directory / filename
    return _csv(str(path), _mtime(path))


@st.cache_data(show_spinner=False, max_entries=14)
def _snapshot(path: str, mtime_ns: int) -> dict:
    if not Path(path).is_file():
        return {}
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return {}


def _num(value):
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def _short_money(number, currency='INR'):
    n = _num(number)
    if n is None:
        return 'N/A'
    if currency == 'INR':
        value = n / 1e7
        if abs(value) >= 1e5:
            return f'₹{value / 1e5:,.2f} L Cr'
        return f'₹{value:,.2f} Cr'
    marker = {'USD': '$', 'EUR': '€', 'GBP': '£'}.get(currency, (currency or '?') + ' ')
    if abs(n) >= 1e9:
        return f'{marker}{n/1e9:,.2f}B'
    if abs(n) >= 1e6:
        return f'{marker}{n/1e6:,.2f}M'
    return f'{marker}{n:,.2f}'


def _fmt(value, kind='money', currency='INR'):
    n = _num(value)
    if n is None:
        return 'N/A'
    if kind == 'money':
        return _short_money(n, currency)
    if kind == 'pct':
        return f'{n*100:+,.1f}%' if n < 0 else f'{n*100:,.1f}%'
    if kind == 'ratio':
        return f'{n:,.2f}×'
    if kind == 'shares':
        return f'{n/1e7:,.2f} Cr'
    if kind == 'price':
        return f'₹{n:,.2f}' if currency == 'INR' else f'{currency} {n:,.2f}'
    return f'{n:,.2f}'


def _tile_group(title: str, metrics: list[tuple[str, float | None, str, str]], currency: str):
    st.markdown(f'<div class="ifr-section">{escape(title)}</div>', unsafe_allow_html=True)
    for start in range(0, len(metrics), 5):
        columns = st.columns(5, gap='small')
        for col, (label, value, kind, desc) in zip(columns, metrics[start:start + 5]):
            col.markdown(
                '<div class="ifr-tile" title="' + escape(desc, quote=True) + '">'
                '<div class="ifr-label">' + escape(label) + '</div>'
                '<div class="ifr-number">' + escape(_fmt(value, kind, currency)) + '</div>'
                '</div>', unsafe_allow_html=True)


def _style():
    apply_research_theme()
    st.markdown('''<style>
    .ifr-kicker {font-size:.75rem;letter-spacing:.13em;color:#56c9f4;font-weight:800}
    .ifr-title {font-size:1.75rem;font-weight:800;color:#f0f7ff;letter-spacing:-.025em;margin:0 0 4px}
    .ifr-muted {color:#a7bbd5;font-size:.88rem;margin-bottom:13px}
    .ifr-section {font-size:1rem;font-weight:700;color:#eaf3ff;margin:14px 0 8px}
    .ifr-tile {background:#142137;border:1px solid #2a3c55;border-radius:9px;min-height:72px;padding:9px 11px;margin-bottom:5px}
    .ifr-label {font-size:.72rem;color:#b6c5d9;line-height:1.17}
    .ifr-number {font-size:1.15rem;color:#f1f7ff;font-weight:750;margin-top:7px;white-space:nowrap}
    .ifr-callout {background:#101e32;border:1px solid #29415c;border-radius:10px;padding:10px 15px;color:#abc1da;margin:10px 0;font-size:.83rem}
    @media(max-width:850px) {.ifr-number{font-size:.84rem}.ifr-tile{padding:8px 5px}}
    </style>''', unsafe_allow_html=True)


def _header(kicker: str, title: str, subtitle: str):
    st.markdown(f'<div class="ifr-kicker">{escape(kicker)}</div><div class="ifr-title">{escape(title)}</div>'
                f'<div class="ifr-muted">{escape(subtitle)}</div>', unsafe_allow_html=True)


def _source_buttons(symbol: str):
    c1, c2 = st.columns(2)
    c1.link_button('↗ Screener · consolidated statements', screener_url(symbol), use_container_width=True)
    c2.link_button('↗ Yahoo Finance · financial statements', f'https://finance.yahoo.com/quote/{symbol}.NS/financials/', use_container_width=True)
    st.caption('Screener is a separate external research source, not a source copied into this dashboard. '
               'Yahoo statement scope (consolidated vs standalone) may differ from Screener. Do not compare them as identical without verification.')


def _row_trace(payload: dict, frequency: str, metric: str) -> tuple[list[str], list[float | None]]:
    group = (payload.get('statements') or {}).get(frequency) or {}
    periods = sorted({p for section in group.values() for p in section}, reverse=True)
    values = [build_kpis(payload, frequency, p)['metrics'].get(metric) for p in periods]
    return periods, values


def _line_chart(payload: dict, frequency: str, metrics: list[tuple[str, str]], currency: str,
                *, percentage=False, title=''):
    fig = go.Figure()
    all_values = False
    for key, label in metrics:
        periods, values = _row_trace(payload, frequency, key)
        if any(v is not None for v in values):
            all_values = True
            ys = [v * 100 if percentage and v is not None else v / 1e7 if v is not None and currency == 'INR' and key in MONEY_METRICS else v for v in values]
            fig.add_trace(go.Scatter(x=periods[::-1], y=ys[::-1], name=label,
                                     mode='lines+markers', connectgaps=False))
    if not all_values:
        st.info(f'{title}: No compatible reporting periods available.')
        return
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(title=title, height=305, margin=dict(l=26, r=16, t=47, b=28),
                      yaxis_title='%' if percentage else ('INR crore' if currency == 'INR' else currency))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def _statement_view(payload: dict, frequency: str):
    group = (payload.get('statements') or {}).get(frequency) or {}
    label = {'income':'Income statement', 'balance':'Balance sheet', 'cashflow':'Cash flow statement'}
    currency = payload.get('currency') or 'unknown'
    for section in ('income', 'balance', 'cashflow'):
        st.markdown(f'#### {label[section]}')
        rows = group.get(section) or {}
        if not rows:
            st.info('No source periods available.')
            continue
        frame = pd.DataFrame.from_dict(rows, orient='index').sort_index(ascending=False).T
        # Preserve source units and avoid dropping missing observations.
        numeric = frame.apply(pd.to_numeric, errors='coerce')
        money = set(numeric.index) & MONEY_METRICS
        if currency == 'INR':
            numeric.loc[list(money)] /= 1e7
            st.caption('Money rows shown in INR crore; diluted EPS in INR/share; shares_statement as share count.')
        else:
            st.caption(f'Money rows are in reported {currency}; EPS per share. Currency not assumed.')
        st.dataframe(numeric, use_container_width=True, height=min(465, 95 + 38*len(frame)))
        st.download_button('⬇ Export ' + label[section].lower(), frame.to_csv().encode('utf-8'),
                           file_name=f"{payload.get('symbol','india')}_{frequency}_{section}.csv",
                           mime='text/csv', key=f'ind_stmt_{frequency}_{section}')


def render_india_company_kpis():
    _style()
    _header('INDIA · FINANCIAL RESEARCH', 'India Company Financial KPIs',
            'NSE constituent universe · Cached Yahoo financial statements · India-specific INR / crore formatting')
    companies = _read(HOLDINGS, 'companies.csv')
    memberships = _read(HOLDINGS, 'constituents.csv')
    summary = _read(DATA, 'company_financial_summary.csv')
    if companies.empty or 'company_key' not in companies:
        st.warning('No Indian constituent directory found. Run India NSE Constituents Refresh before financial-data collection.')
        return
    companies = companies.drop_duplicates(subset=['company_key'])
    company_map = {row['company_key']: row for _, row in companies.iterrows()}
    keys = list(company_map)
    if not keys:
        st.info('No NSE companies available.')
        return
    requested_symbol = str(st.session_state.get('india_financial_symbol', '')).strip().upper()
    default = next((i for i,k in enumerate(keys) if company_map[k]['symbol'] == requested_symbol), 0)
    c1, c2, c3 = st.columns([3.1, 1.2, 1.25])
    selection = c1.selectbox('NSE company (all tracked constituents)', keys,
        index=default, format_func=lambda k: f"{company_map[k]['symbol']}  ·  {company_map[k]['company_name']}",
        key='india_financial_select')
    frequency = c2.selectbox('Reporting', ['annual','quarterly'], format_func=str.title, key='india_fin_freq')
    company = company_map[selection]
    symbol = company['symbol']
    company_path = company_file(selection)
    payload = _snapshot(str(company_path), _mtime(company_path))
    c3.metric('Financial data', 'Cached' if payload else 'Pending')
    if not payload:
        st.warning(f'No saved Yahoo financial statements for {symbol} yet. '
                   'Run **GitHub Actions → India Company Financials Refresh** with symbol '
                   f'`{symbol}` or use the regular 25-company batches. The page does not contact Yahoo live.')
        _source_buttons(symbol)
        if not summary.empty:
            st.caption(f'{len(summary)} of {len(companies)} companies have a saved financial snapshot.')
        return
    if payload.get('company_key') != selection:
        st.error('Cached financial record does not match selected NSE company identity.')
        return
    if frequency not in payload.get('statements', {}):
        st.warning('The saved financial-data file lacks this reporting frequency.')
        return
    periods = sorted({d for part in payload['statements'][frequency].values() for d in part}, reverse=True)
    if not periods:
        st.warning('No verified data for the selected reporting frequency.')
        return
    period = st.selectbox('Fiscal period ending', periods, key='india_fin_period')
    result = build_kpis(payload, frequency, period)
    metrics = result['metrics']
    cur = payload.get('currency') or 'unknown'
    quote_cur = (payload.get('quote') or {}).get('currency') or 'unknown'
    st.markdown(f'### {escape(company["company_name"])} · {escape(symbol)}')
    st.caption(f"ISIN {company.get('isin') or 'N/A'} · Yahoo {payload.get('yahoo_ticker')} · "
               f"Financial currency {cur} · Snapshot {payload.get('retrieved_utc') or 'unknown'} · "
               f"Fiscal period {period}")
    if any(metrics.get(key) is None for key in ('revenue', 'total_assets')):
        st.info('Some financial-statement inputs are missing. Missing values are shown as N/A; no zeros are imputed.')
    if any(x in (company.get('industry', '') + ' ' + payload.get('sector', '')).lower() for x in ('bank', 'insurance', 'financial services', 'credit')):
        st.warning('Financial institution: generic leverage, cash-flow and enterprise-value ratios may not be economically comparable. '
                   'Use bank/insurer-specific disclosures before drawing conclusions.')
    memberships_this = memberships[memberships['company_key'] == selection] if not memberships.empty else pd.DataFrame()
    st.caption(f"NSE constituent memberships: {len(memberships_this)} · Source industry: {company.get('industry') or 'not specified'}")
    tabs = st.tabs(['Overview', 'Growth & Margins', 'Balance Sheet', 'Cash Flow',
                    'Asset & Intrinsic Value', 'Trends', 'Statements', 'Sources & Holdings'])
    with tabs[0]:
        _tile_group('At a glance', [
            ('Revenue', metrics.get('revenue'), 'money','Fiscal period revenue'),
            ('Net income', metrics.get('net_income'), 'money','Net income attributable to shareholders if available'),
            ('Diluted EPS', metrics.get('diluted_eps'), 'price','INR per share if financial currency INR'),
            ('Operating margin', metrics.get('operating_margin'), 'pct','Operating income / revenue'),
            ('Free cash flow', metrics.get('free_cash_flow'), 'money','OCF less capital expenditure'),
            ('Total debt', metrics.get('total_debt'), 'money','Total borrowings when published; not inferred from long-term debt alone'),
            ('Return on equity', metrics.get('roe'), 'pct','Net income / period-end common equity'),
            ('Book value/share', metrics.get('book_value_per_share'), 'price','Period-end common equity / shares'),
            ('Graham Number', metrics.get('graham_number'), 'price','sqrt(22.5 * diluted EPS * book value per share)'),
            ('Price / earnings', metrics.get('pe'), 'ratio','Market quote / positive EPS; matching currencies required'),
        ], cur)
        c1, c2 = st.columns(2)
        with c1:
            _line_chart(payload, frequency, [('revenue', 'Revenue'), ('net_income', 'Net income')], cur,
                        title='Revenue & net income history')
        with c2:
            _line_chart(payload, frequency, [('total_debt', 'Total debt'), ('cash', 'Cash')], cur,
                        title='Debt & cash history')
    with tabs[1]:
        _tile_group('Financial growth', [
            ('Revenue YoY', metrics.get('revenue_yoy'), 'pct','Consecutive annual periods only'),
            ('Net income YoY', metrics.get('earnings_yoy'), 'pct','Positive-base annual growth'),
            ('EPS YoY', metrics.get('eps_yoy'), 'pct','Positive-base annual growth'),
            ('Revenue 3Y CAGR', metrics.get('revenue_3y_cagr'), 'pct','Three-year fiscal period comparison'),
            ('Revenue 5Y CAGR', metrics.get('revenue_5y_cagr'), 'pct','Five-year fiscal period comparison'),
        ], cur)
        _tile_group('Margins & returns', [
            ('Gross margin', metrics.get('gross_margin'), 'pct','Gross profit/revenue'),
            ('Operating margin', metrics.get('operating_margin'), 'pct','Operating income/revenue'),
            ('Net margin', metrics.get('net_margin'), 'pct','Net income/revenue'),
            ('FCF margin', metrics.get('fcf_margin'), 'pct','Free cash flow/revenue'),
            ('ROE', metrics.get('roe'), 'pct','Net income / period-end common equity'),
            ('ROA', metrics.get('roa'), 'pct','Net income / period-end assets'),
        ], cur)
    with tabs[2]:
        _tile_group('Assets & liabilities', [
            ('Assets', metrics.get('total_assets'), 'money','Period-end total assets'),
            ('Liabilities', metrics.get('total_liabilities'), 'money','Period-end total liabilities'),
            ('Common equity', metrics.get('equity'), 'money','Stockholders equity'),
            ('Cash', metrics.get('cash'), 'money','Cash and equivalents; may include short-term investments where Yahoo has only combined row'),
            ('Total debt', metrics.get('total_debt'), 'money','Full total debt only when published'),
            ('Net debt', metrics.get('net_debt'), 'money','Total debt less cash'),
            ('Current ratio', metrics.get('current_ratio'), 'ratio','Current assets/current liabilities'),
            ('Debt/equity', metrics.get('debt_to_equity'), 'ratio','Total debt/common equity'),
            ('Net debt/EBITDA', metrics.get('net_debt_to_ebitda'), 'ratio','Net debt/EBITDA when comparable'),
            ('Interest coverage', metrics.get('interest_coverage'), 'ratio','Operating income / interest expense'),
        ], cur)
    with tabs[3]:
        _tile_group('Cash flow & allocation', [
            ('Operating cash flow', metrics.get('operating_cash_flow'), 'money','CFO reported by Yahoo'),
            ('Capital expenditure', metrics.get('capital_expenditure'), 'money','Absolute capex outflows'),
            ('Free cash flow', metrics.get('free_cash_flow'), 'money','CFO less capex'),
            ('FCF margin', metrics.get('fcf_margin'), 'pct','FCF/revenue'),
            ('Cash conversion', metrics.get('cash_conversion'), 'ratio','CFO/net income'),
            ('Dividends paid', metrics.get('dividends_paid'), 'money','Cash dividends outflow if available'),
            ('Share buybacks', metrics.get('repurchases'), 'money','Cash repurchases if reported'),
        ], cur)
    with tabs[4]:
        _tile_group('Asset & Graham value per share', [
            ('Book value / share', metrics.get('book_value_per_share'), 'price','Common equity per share'),
            ('Tangible book / share', metrics.get('tangible_book_per_share'), 'price','Requires goodwill and intangible details'),
            ('NCAV / share', metrics.get('ncav_per_share'), 'price','Current assets less all liabilities and verified preferred claims'),
            ('Graham Number', metrics.get('graham_number'), 'price','Graham value screen, not a guaranteed fair value'),
        ], cur)
        _tile_group('Market quote · provider currency, not financial reporting currency', [
            ('Current price', metrics.get('price'), 'price','Cached Yahoo quote'),
            ('Market cap', metrics.get('market_cap'), 'money','Yahoo as-of quote snapshot'),
            ('P/E', metrics.get('pe'), 'ratio','Price / positive diluted EPS'),
            ('P/B', metrics.get('pb'), 'ratio','Price/book value per share'),
            ('FCF yield', metrics.get('fcf_yield'), 'pct','Historical annual FCF / market cap'),
            ('Enterprise value', metrics.get('enterprise_value'), 'money','Market cap + verified debt - cash'),
        ], quote_cur)
        st.markdown('#### Intrinsic value · illustrative cash-flow model')
        with st.expander('Adjust DCF assumptions', expanded=False):
            x, y, z = st.columns(3)
            growth = x.number_input('FCF growth (%)', min_value=-15.0, max_value=35.0, value=7.0, step=0.5, key='in_dcf_growth')
            discount = y.number_input('Required return (%)', min_value=1.0, max_value=45.0, value=13.0, step=0.5, key='in_dcf_discount')
            terminal = z.number_input('Terminal growth (%)', min_value=-2.0, max_value=9.0, value=4.0, step=0.5, key='in_dcf_terminal')
        dcf = (equity_dcf_proxy(metrics.get('free_cash_flow'), metrics.get('shares_outstanding'),
                               growth, discount, terminal) if frequency == 'annual' else None)
        st.metric('5-year equity FCF-proxy DCF / share', _fmt(dcf, 'price', cur))
        st.caption('Simplified present value of projected free cash flow per share; **not true FCFE** and not an acquisition valuation. '
                   'Only meaningful for positive cash flow. Requires discount rate above terminal growth. No invented inputs.')
        st.markdown('#### Estimated liquidation recovery · optional scenario')
        c1, c2 = st.columns(2)
        recovery = c1.slider('Noncash asset recovery (%)', 0, 100, 55, 5, key='in_liq_recovery')
        costs = c2.slider('Liquidation costs (% of proceeds)', 0, 25, 5, 1, key='in_liq_costs')
        no_pref_assumed = st.checkbox('Scenario assumption: no preferred equity claims (not independently verified)', value=False,
                                     key='in_liq_no_pref')
        claims = metrics.get('preferred_equity')
        if claims is None and no_pref_assumed:
            claims = 0.0
        lq = liquidation_proxy(metrics.get('total_assets'), metrics.get('cash'),
               metrics.get('total_liabilities'), metrics.get('shares_outstanding'),
               recovery, costs, preferred_claim=claims)
        st.metric('Hypothetical recovery / common share', _fmt(lq, 'price', cur))
        st.caption('Not an appraisal or guaranteed payout. N/A when preferred-equity obligations are unknown. '
                   'No tax, off-balance liabilities, bankruptcy priority or asset-specific valuations are verified.')
    with tabs[5]:
        c1, c2 = st.columns(2)
        with c1:
            _line_chart(payload, frequency, [('revenue','Revenue'),('operating_income','Operating income'),
                                                  ('net_income','Net income')], cur, title='Revenue · earnings')
        with c2:
            _line_chart(payload, frequency, [('gross_margin','Gross margin'),('operating_margin','Operating margin'),
                                                  ('net_margin','Net margin')], cur, percentage=True, title='Profitability trends')
        c1, c2 = st.columns(2)
        with c1:
            _line_chart(payload, frequency, [('operating_cash_flow','Operating cash flow'),
                                             ('free_cash_flow','Free cash flow')], cur, title='Cash-flow trends')
        with c2:
            _line_chart(payload, frequency, [('cash','Cash'),('total_debt','Total debt')], cur,
                        title='Cash & borrowing trends')
        st.caption('Quarterly values are Yahoo provider-reported quarters; missing Q4/other periods are not imputed. '
                   'Balance-sheet trends are period-end stocks, not cash-flow amounts. Dates are sorted chronologically.')
    with tabs[6]:
        _statement_view(payload, frequency)
    with tabs[7]:
        _source_buttons(symbol)
        st.markdown('#### Original NSE index membership')
        if memberships_this.empty:
            st.info('No current NSE memberships in the saved universe.')
        else:
            columns = [x for x in ('index_name','category','factor_family','parent_universe','source_url') if x in memberships_this]
            st.dataframe(memberships_this[columns].rename(columns={
                'index_name':'Index','category':'Category','factor_family':'Factor family',
                'parent_universe':'Parent universe','source_url':'Official NSE file'}),
                use_container_width=True, hide_index=True, height=340,
                column_config={'Official NSE file': st.column_config.LinkColumn('Official NSE file', display_text='NSE source')})
        st.markdown('#### Source dates and data lineage')
        sources = result.get('source_periods', {})
        details = pd.DataFrame([{'Dataset':name, 'Financial period': date or 'N/A'} for name,date in sources.items()])
        st.dataframe(details, use_container_width=True, hide_index=True)
        st.caption(f"Financial retrieval UTC: {payload.get('retrieved_utc') or 'N/A'} · "
                   f"Market snapshot retrieved UTC: {(payload.get('quote') or {}).get('asof_utc') or 'N/A'} · "
                   f"Yahoo financial currency: {cur} · Market quote currency: {(payload.get('quote') or {}).get('currency') or 'unknown'}")
        if metrics.get('share_basis') == 'current_quote':
            st.warning('Per-share ratios may divide historical statement values by current reported shares. '
                       'Historical period share count was unavailable. Interpret per-share asset values with caution.')
        st.caption(payload.get('statement_scope', 'Yahoo statement consolidation scope not verified.'))
        if payload.get('source_notes'):
            with st.expander('Source request warnings'):
                st.write(payload['source_notes'])


def _aggregation_table(frame: pd.DataFrame, records: pd.DataFrame, group_type: str, membership_group=''):
    if frame.empty or records.empty:
        st.info('No valid NSE + Yahoo merged data available. Run the two refresh workflows to populate coverage.')
        return
    view = frame[frame['group_type'] == group_type].copy()
    if membership_group:
        pass
    if view.empty:
        st.info('No saved metrics for this grouping.')
        return
    rename = {
        'group_name':'Index / factor family', 'parent_universe':'Parent',
        'constituents':'NSE constituents', 'companies_with_snapshots':'Yahoo snapshots',
        'annual_income_coverage':'Annual income', 'annual_balance_coverage':'Balance sheets',
        'annual_cashflow_coverage':'Cash flows', 'price_coverage':'Market quotes',
        'pct_with_income':'Revenue coverage %',
        'median_revenue_yoy':'Median sales YoY', 'median_operating_margin':'Median operating margin',
        'median_net_margin':'Median net margin', 'median_roe':'Median ROE',
        'median_fcf_margin':'Median FCF margin', 'median_pe':'Median P/E',
        'median_fcf_yield':'Median FCF yield',
    }
    view = view.rename(columns=rename)
    measure_cols = ['Index / factor family','Parent','NSE constituents','Yahoo snapshots','Annual income',
                    'Balance sheets','Cash flows','Market quotes','Revenue coverage %',
                    'Median sales YoY','Median operating margin','Median net margin',
                    'Median ROE','Median FCF margin','Median P/E','Median FCF yield']
    for col in measure_cols[2:]:
        view[col] = pd.to_numeric(view[col], errors='coerce')
    for col in ('Median sales YoY','Median operating margin','Median net margin',
                'Median ROE','Median FCF margin','Median FCF yield'):
        view[col] = view[col] * 100
    st.caption('Unweighted company-level medians · NSE membership-based groups · No holdings weights or company rankings.')
    chart_names = view['Index / factor family'].tolist()
    coverage_values = [100 * a/b if b else 0 for a, b in zip(view['Annual income'], view['NSE constituents'])]
    plot = go.Figure(go.Bar(x=coverage_values, y=chart_names, orientation='h',
                            marker_color='#51b7e8', hovertemplate='%{y}<br>Annual income coverage: %{x:.1f}%<extra></extra>'))
    plot.update_layout(**PLOTLY_LAYOUT)
    plot.update_layout(height=max(245, min(750, 40*len(view))), xaxis_title='Annual income coverage (%)',
                       yaxis=dict(autorange='reversed'), margin=dict(l=8, r=10, t=20, b=30))
    st.plotly_chart(plot, use_container_width=True, config={'displayModeBar': False})
    st.dataframe(view[measure_cols], use_container_width=True, hide_index=True, height=415,
                 column_config={
                     'Revenue coverage %': st.column_config.NumberColumn(format='%.0f%%'),
                     'Median sales YoY': st.column_config.NumberColumn(format='%.2f'),
                     'Median operating margin': st.column_config.NumberColumn(format='%.2f'),
                     'Median net margin': st.column_config.NumberColumn(format='%.2f'),
                     'Median ROE': st.column_config.NumberColumn(format='%.2f'),
                     'Median FCF margin': st.column_config.NumberColumn(format='%.2f'),
                     'Median FCF yield': st.column_config.NumberColumn(format='%.2f'),
                 })
    st.caption('Median percentage columns are displayed as %; P/E is a multiple. Coverage and sample sizes differ across indices.')
    st.download_button('⬇ Export financial aggregation', view.to_csv(index=False).encode('utf-8'),
                       file_name=f'india_{group_type.lower().replace(" ", "_")}_financials.csv', mime='text/csv')


def _group_company_detail(memberships: pd.DataFrame, company_fin: pd.DataFrame, *, label_key='index_name', group=None):
    options = sorted(memberships[label_key].dropna().unique())
    if not options:
        return
    name = st.selectbox('Inspect constituent financials for', options, key='india_group_selector_' + label_key)
    if label_key == 'factor_family':
        selection = memberships[(memberships['category'] == 'Factor') & (memberships[label_key] == name)]
    else:
        selection = memberships[memberships[label_key] == name]
    unique = selection.drop_duplicates('company_key')
    if company_fin.empty or 'company_key' not in company_fin:
        st.info(f'{len(unique)} NSE companies are members; Yahoo financial snapshots are not cached yet.')
        return
    merged = unique[['company_key', 'company_name', 'symbol', 'isin']].merge(company_fin, how='left', on='company_key', suffixes=('', '_y'))
    display = merged[['company_name','symbol','isin','financial_period','revenue_yoy',
                      'operating_margin','net_margin','roe','fcf_margin','pe','retrieved_utc']].copy()
    display.columns = ['Company','NSE Symbol','ISIN','Fiscal period','Revenue YoY','Operating margin',
                       'Net margin','ROE','FCF margin','P/E','Yahoo snapshot UTC']
    st.caption(f'{len(unique):,} verified NSE members · {merged["financial_period"].replace("", pd.NA).notna().sum():,} with annual financial periods.')
    st.dataframe(display, hide_index=True, use_container_width=True, height=365)
    st.download_button('⬇ Download group constituents and KPIs', display.to_csv(index=False).encode('utf-8'),
                       file_name='india_group_constituent_financials.csv', mime='text/csv')
    if len(unique):
        co1, co2 = st.columns([2.1, 1.0])
        chosen_key = co1.selectbox('View financial KPIs for one constituent', list(unique['company_key']),
                                  format_func=lambda k: str(unique.loc[unique['company_key'] == k, 'symbol'].iloc[0]),
                                  key='india_group_drill_' + label_key)
        if co2.button('📊 Open company KPIs', key='india_group_open_' + label_key):
            chosen_symbol = str(unique.loc[unique['company_key'] == chosen_key, 'symbol'].iloc[0]).upper()
            st.session_state.india_financial_symbol = chosen_symbol
            st.session_state.pop('india_financial_select', None)
            st.session_state.selected_page = 'India Company Financial KPIs'
            st.rerun()


def _factor_sector_heatmap(memberships: pd.DataFrame, summary: pd.DataFrame):
    factors = memberships[memberships['category'] == 'Factor']
    sector = memberships[memberships['category'].isin(['Sector','Thematic'])]
    if factors.empty or sector.empty:
        st.info('NSE sector/factor membership data missing.')
        return
    family_members = {f:set(g['company_key']) for f,g in factors.groupby('factor_family')}
    sector_members = {s:set(g['company_key']) for s,g in sector.groupby('index_name')}
    financial_keys = set(summary['company_key']) if 'company_key' in summary else set()
    mode = st.radio('Intersection measure', ['Verified shared constituents','Shared companies with Yahoo snapshots'],
                    horizontal=True, key='india_intersection_measure')
    cells = []
    for s, s_keys in sorted(sector_members.items()):
        row = {'Index':s}
        for f, f_keys in sorted(family_members.items()):
            shared = s_keys & f_keys
            if mode.startswith('Shared companies'):
                shared &= financial_keys
            row[f] = len(shared)
        cells.append(row)
    matrix = pd.DataFrame(cells).set_index('Index')
    fig = go.Figure(go.Heatmap(z=matrix.to_numpy(dtype=int),x=matrix.columns.tolist(),
                y=matrix.index.tolist(),colorscale=[[0,'#12213a'],[0.4,'#226388'],[1,'#47c5eb']],
                text=matrix.astype(str).to_numpy(), texttemplate='%{text}',
                hovertemplate='%{y} × %{x}<br>Companies: %{z}<extra></extra>'))
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(height=max(460, 27*len(matrix)), margin=dict(l=25,r=15,t=15,b=80),
                      xaxis=dict(side='top'))
    st.plotly_chart(fig, use_container_width=True)
    st.caption('Overlap uses unique NSE company identifiers. The second option counts only companies with a saved Yahoo snapshot, not companies meeting any return threshold.')
    st.download_button('⬇ Export intersection matrix', matrix.to_csv().encode('utf-8'),
                       file_name='india_sector_factor_financial_coverage_matrix.csv', mime='text/csv')


def render_india_sector_factor_financials():
    _style()
    _header('INDIA · NSE HOLDINGS × FINANCIALS', 'India Sector & Factor Financial Analysis',
            '31 NSE indices · unique constituents · Yahoo company financials · descriptive group medians, not index returns or rankings')
    memberships = _read(HOLDINGS, 'constituents.csv')
    aggregates = _read(DATA, 'index_financial_summary.csv')
    financials = _read(DATA, 'company_financial_summary.csv')
    companies = _read(HOLDINGS, 'companies.csv')
    if memberships.empty or companies.empty:
        st.warning('NSE constituent data is missing. Run India NSE Constituents Refresh and commit its generated files.')
        return
    count_fin = len(financials)
    counts = st.columns(4)
    counts[0].metric('NSE securities', len(companies))
    counts[1].metric('Verified index memberships', len(memberships))
    counts[2].metric('Yahoo company snapshots', count_fin)
    counts[3].metric('Annual income statements', int((financials['income_period'] != '').sum()) if 'income_period' in financials else 0)
    st.markdown('<div class="ifr-callout">NSE index membership does not provide an allocation weight. '
        'Sector and factor measures below are unweighted company medians, never weighted index fundamentals. '
        'Factor families merge duplicate company memberships across their different Nifty parent universes.</div>',
        unsafe_allow_html=True)
    if aggregates.empty or 'group_type' not in aggregates:
        st.warning('Financial group data has not been built. Run **GitHub Actions → India Company Financials Refresh**, '
                   'or `python scripts/refresh_india_financials.py --rebuild-only` after downloading NSE constituents.')
        return
    tabs = st.tabs(['Sector & thematic', 'Factor families', 'All source indices', 'Sector × factor matrix', 'Coverage & diagnostics'])
    with tabs[0]:
        names = set(memberships.loc[memberships['category'].isin(['Sector','Thematic']),'index_slug'])
        sector_aggs = aggregates[aggregates['index_slug'].isin(names)]
        _aggregation_table(sector_aggs, memberships, 'Index')
        st.markdown('#### Sector constituent-level financials')
        _group_company_detail(memberships[memberships['category'].isin(['Sector','Thematic'])], financials)
    with tabs[1]:
        _aggregation_table(aggregates, memberships, 'Factor Family')
        st.markdown('#### Factor family company KPIs')
        _group_company_detail(memberships[memberships['category'] == 'Factor'], financials, label_key='factor_family')
    with tabs[2]:
        _aggregation_table(aggregates, memberships, 'Index')
        st.markdown('#### Index constituent research')
        _group_company_detail(memberships, financials)
    with tabs[3]:
        _factor_sector_heatmap(memberships, financials)
    with tabs[4]:
        status = _read(DATA, 'refresh_status.csv')
        st.markdown('#### Financial coverage & provider reliability')
        if status.empty:
            st.info('No Yahoo financial refresh has been attempted yet.')
        else:
            fails = status[status['status'] != 'ok']
            if not fails.empty:
                st.warning(f'{len(fails)} companies most recently failed Yahoo collection. Previous valid snapshots, if any, are preserved.')
                st.dataframe(fails, use_container_width=True, hide_index=True, height=340)
            else:
                st.success('No failures recorded in the saved provider status file.')
        st.markdown('**Data sources & limitations**')
        st.markdown('NSE: membership, ISIN, sector/factor index and observed entry/exit events. '
                    'Yahoo Finance via yfinance: annual/quarterly company statements and cached price reference. '
                    'Screener.in: direct consolidated report for independent research, not scraped or republished. '
                    'Unpublished constituent weights remain unknown. Company financials may be standalone or consolidated depending on Yahoo; scope is not assumed.')
        st.caption('Run the scheduled GitHub Actions refresh to update provider snapshots without blocking the Streamlit app.')
