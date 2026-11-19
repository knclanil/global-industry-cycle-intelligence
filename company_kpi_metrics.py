"""Dedicated, on-demand financial KPI dashboard using existing SEC statement cache."""
import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from research_theme import apply_research_theme, PLOTLY_LAYOUT
from sec_financials import load_company, statements, is_bank


def _value(df, label, period):
    if label not in df.index or period not in df.columns:
        return None
    v = pd.to_numeric(pd.Series([df.at[label, period]]), errors='coerce').iloc[0]
    return float(v) if pd.notna(v) else None


def _ratio(a, b):
    return a / b if a is not None and b is not None and b != 0 else None


def _display(v, kind='money'):
    if v is None or pd.isna(v):
        return 'N/A'
    if kind == 'percent':
        return f'{v * 100:,.1f}%'
    if kind == 'multiple':
        return f'{v:,.2f}×'
    if kind == 'eps':
        return f'${v:,.2f}'
    if abs(v) >= 1e12:
        return f'${v / 1e12:,.2f}T'
    if abs(v) >= 1e9:
        return f'${v / 1e9:,.2f}B'
    if abs(v) >= 1e6:
        return f'${v / 1e6:,.2f}M'
    return f'${v:,.0f}'


def _card_group(title, metrics):
    """Compact KPI tiles; omit repetitive captions from the main viewport."""
    st.markdown(f'<div class="kpi-section-title">{title}</div>', unsafe_allow_html=True)
    for start in range(0, len(metrics), 5):
        cols = st.columns(5, gap='small')
        for col, (label, val, kind, note) in zip(cols, metrics[start:start + 5]):
            with col:
                st.markdown(
                    '<div class="kpi-tile" title="' + __import__('html').escape(note, quote=True) + '">'
                    '<div class="kpi-label">' + __import__('html').escape(label) + '</div>'
                    '<div class="kpi-number">' + __import__('html').escape(_display(val, kind)) + '</div>'
                    '</div>', unsafe_allow_html=True,
                )


def _growth(df, label, periods, span=1):
    if len(periods) <= span:
        return None
    latest, earlier = _value(df, label, periods[0]), _value(df, label, periods[span])
    return _ratio(latest - earlier, abs(earlier)) if latest is not None and earlier is not None else None


def _cagr(df, label, periods, years):
    if len(periods) <= years:
        return None
    first, last = _value(df, label, periods[years]), _value(df, label, periods[0])
    if first is None or last is None or first <= 0 or last <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def _chart(title, periods, items, kind='money'):
    fig = go.Figure()
    for label, values in items:
        if any(v is not None for v in values):
            fig.add_trace(go.Scatter(x=periods[::-1], y=values[::-1], mode='lines+markers', name=label,
                                     connectgaps=False))
    if not fig.data:
        st.info(f'{title}: insufficient verified historical data.')
        return
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(title=title, height=330, margin=dict(l=35, r=20, t=55, b=40),
                      yaxis_title='Percent' if kind == 'percent' else 'USD billions')
    st.plotly_chart(fig, use_container_width=True)


def render_company_kpi_metrics():
    apply_research_theme()
    st.markdown('''<style>
    .kpi-section-title {font-size:1.02rem;font-weight:700;color:#e8f2ff;margin:14px 0 9px}
    .kpi-tile {background:#142137;border:1px solid #2a3c55;border-radius:10px;
        min-height:78px;padding:10px 12px;margin-bottom:5px;}
    .kpi-label {font-size:.74rem;color:#afc2d9;line-height:1.2;min-height:18px}
    .kpi-number {font-size:1.23rem;font-weight:700;color:#f1f7ff;margin-top:6px;white-space:nowrap}
    @media(max-width:800px){.kpi-number{font-size:.95rem}.kpi-tile{padding:8px 6px}}
    </style>''', unsafe_allow_html=True)
    st.title('📊 Company Financial KPI Intelligence')
    st.caption('Dedicated fundamental KPI workspace · official SEC financial statements · dark dashboard theme')
    st.caption('One company at a time · Verified SEC statements · N/A means unavailable')
    with st.form('kpi_company_form'):
        ticker = st.text_input('Company ticker', value=st.session_state.get('kpi_ticker', st.session_state.get('research_ticker', 'AAPL'))).strip().upper()
        submit = st.form_submit_button('Analyze financial KPIs', type='primary')
    if submit:
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,14}', ticker):
            st.error('Enter a valid ticker.')
            return
        st.session_state.kpi_ticker = ticker
        st.session_state.kpi_loaded = ticker
    if not st.session_state.get('kpi_loaded'):
        st.caption('Choose a ticker and click Analyze financial KPIs to begin.')
        return
    ticker = st.session_state.kpi_loaded
    try:
        data, cik, name = load_company(ticker)
        result = statements(data, 'annual', 10, ticker=ticker)
    except Exception as exc:
        st.warning(f'Financial KPI data unavailable for {ticker}: {exc}')
        st.caption('The SEC cache may not yet contain this issuer. Run the background fundamentals refresh.')
        return
    inc, bs, cf = (result[k][0] for k in ('Income Statement', 'Balance Sheet', 'Cash Flow'))
    periods = sorted(set(inc.columns) | set(bs.columns) | set(cf.columns), reverse=True)
    if not periods:
        st.warning('No usable annual reporting periods were found.')
        return
    selected = st.selectbox('Financial reporting period', periods, index=0)
    bank = is_bank(data, ticker)
    st.subheader(f'{name} · {ticker}')
    st.caption(f'SEC CIK {cik:010d} · Fiscal period ending {selected} · Annual reporting · USD unless stated otherwise')
    if bank:
        st.warning('Bank financial statements need industry-specific capital and credit-quality metrics. Generic leverage and operating metrics below are not interpreted as bank health scores.')
    i = lambda label: _value(inc, label, selected)
    b = lambda label: _value(bs, label, selected)
    c = lambda label: _value(cf, label, selected)
    rev, net, op, gross, eps = (i(x) for x in ('Revenue', 'Net income', 'Operating income', 'Gross profit', 'Diluted EPS'))
    assets, liabilities, equity = (b(x) for x in ('Total assets', 'Total liabilities', 'Stockholders equity'))
    cash, debt, ca, cl = (b(x) for x in ('Cash and equivalents', 'Long-term debt', 'Current assets', 'Current liabilities'))
    ocf, fcf, capex = (c(x) for x in ('Operating cash flow', 'Free cash flow', 'Capital expenditures'))
    # Debt is long-term debt only; do not call it total debt.
    net_lt_debt = debt - cash if debt is not None and cash is not None else None
    year_periods = sorted(inc.columns, reverse=True)
    if selected in year_periods:
        year_periods = year_periods[year_periods.index(selected):]
    else:
        year_periods = []
    tab_summary, tab_growth, tab_strength, tab_cash, tab_value, tab_trends = st.tabs(['Overview', 'Growth & Margins', 'Balance Sheet', 'Cash Flow', 'Asset & Intrinsic Value', 'Trends'])
    with tab_growth:
        _card_group('Growth & earnings', [
        ('Revenue', rev, 'money', 'Reported annual revenue'),
        ('Net income', net, 'money', 'Reported annual earnings'),
        ('Diluted EPS', eps, 'eps', 'USD per diluted share'),
        ('Revenue YoY', _growth(inc, 'Revenue', year_periods), 'percent', 'Previous available annual period; check dates'),
        ('Net income YoY', _growth(inc, 'Net income', year_periods), 'percent', 'Previous available annual period; check dates'),
        ('EPS YoY', _growth(inc, 'Diluted EPS', year_periods), 'percent', 'Previous available annual period; check dates'),
        ('Revenue 3Y CAGR', _cagr(inc, 'Revenue', year_periods, 3), 'percent', 'Requires four consecutive fiscal years'),
        ('Revenue 5Y CAGR', _cagr(inc, 'Revenue', year_periods, 5), 'percent', 'Requires six consecutive fiscal years'),
        ('EPS 5Y CAGR', _cagr(inc, 'Diluted EPS', year_periods, 5), 'percent', 'Positive start and end EPS required'),
        ('FCF YoY', _growth(cf, 'Free cash flow', sorted(cf.columns, reverse=True)), 'percent', 'Available fiscal years; not TTM'),
    ])
    with tab_growth:
        _card_group('Profitability & capital efficiency', [
        ('Gross margin', _ratio(gross, rev), 'percent', 'Gross profit / revenue'),
        ('Operating margin', _ratio(op, rev), 'percent', 'Operating income / revenue'),
        ('Net margin', _ratio(net, rev), 'percent', 'Net income / revenue'),
        ('FCF margin', _ratio(fcf, rev), 'percent', 'Free cash flow / revenue'),
        ('ROE (period-end)', _ratio(net, equity) if equity is not None and equity > 0 else None, 'percent', 'Net income / period-end equity; not average ROE'),
        ('ROA (period-end)', _ratio(net, assets), 'percent', 'Net income / period-end assets; not average ROA'),
        ('ROIC', None, 'percent', 'Requires verified NOPAT and invested capital'),
        ('EBITDA margin', None, 'percent', 'Requires verified depreciation/amortization'),
    ])
    with tab_strength:
        _card_group('Balance sheet & financial strength', [
        ('Total assets', assets, 'money', 'Period-end assets'),
        ('Total liabilities', liabilities, 'money', 'Period-end liabilities'),
        ('Stockholders equity', equity, 'money', 'Period-end equity'),
        ('Cash & equivalents', cash, 'money', 'Reported cash balance'),
        ('Long-term debt', debt, 'money', 'Only reported long-term debt concept'),
        ('Long-term debt less cash', net_lt_debt, 'money', 'Not full net debt; short-term debt excluded'),
        ('Long-term debt / equity', _ratio(debt, equity) if equity is not None and equity > 0 else None, 'multiple', 'Excludes other borrowings'),
        ('Current ratio', _ratio(ca, cl), 'multiple', 'Current assets / current liabilities'),
        ('Net debt / EBITDA', None, 'multiple', 'Requires verified total debt and EBITDA'),
        ('Interest coverage', None, 'multiple', 'Requires comparable interest expense'),
        ('Quick ratio', None, 'multiple', 'Requires inventory and other current-asset detail'),
        ('Debt maturity profile', None, 'money', 'Requires debt maturity disclosures'),
    ])
    with tab_cash:
        _card_group('Cash flow & capital allocation', [
        ('Operating cash flow', ocf, 'money', 'Reported cash from operations'),
        ('Capital expenditures', capex, 'money', 'Reported purchases of PP&E'),
        ('Free cash flow', fcf, 'money', 'OCF less absolute capital expenditures'),
        ('OCF / net income', _ratio(ocf, net), 'multiple', 'Cash conversion before capex'),
        ('FCF / net income', _ratio(fcf, net), 'multiple', 'Cash conversion after capex'),
        ('Capex / revenue', _ratio(abs(capex), rev) if capex is not None else None, 'percent', 'Reinvestment intensity'),
        ('Dividends paid', c('Dividends paid'), 'money', 'Reported dividends paid'),
        ('Share repurchases', c('Share repurchases'), 'money', 'Reported common share buybacks'),
        ('FCF 5Y CAGR', _cagr(cf, 'Free cash flow', sorted(cf.columns, reverse=True), 5), 'percent', 'Positive FCF endpoints required'),
        ('Share count change', None, 'percent', 'Requires comparable historical shares outstanding'),
    ])
    with tab_value:
        from asset_valuation import render_asset_valuation
        render_asset_valuation(data, selected, assets, liabilities, equity, ca, net, eps, fcf, bank=bank)
    with tab_trends:
        st.markdown('### Financial performance trends')
        frequency = st.radio('Reporting frequency', ['Annual', 'Quarterly'],
                             horizontal=True, key='kpi_trends_frequency')
        if frequency == 'Quarterly':
            st.caption('Standalone fiscal quarters from SEC 10-Q filings. Cash flow is shown only when a verified standalone quarter is available; missing quarters are not estimated.')
            q_count = st.select_slider('Quarters to display', options=[4, 8, 12, 16, 20], value=12,
                                       key='kpi_trends_quarters')
            try:
                quarterly = statements(data, 'quarterly', q_count, ticker=ticker)
                t_inc, t_bs, t_cf = (quarterly[k][0] for k in ('Income Statement', 'Balance Sheet', 'Cash Flow'))
            except Exception as exc:
                st.warning(f'Quarterly financial statements unavailable: {exc}')
                t_inc, t_bs, t_cf = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            hist = sorted(set(t_inc.columns) | set(t_bs.columns) | set(t_cf.columns), reverse=True)[:q_count]
            if hist:
                st.caption('Period labels are actual SEC reporting end dates. 10-K-only fourth-quarter flow data may be absent; no annual totals are treated as quarterly amounts.')
        else:
            t_inc, t_bs, t_cf = inc, bs, cf
            years = st.select_slider('Years to display', options=[3, 5, 7, 10], value=10,
                                     key='kpi_trends_years')
            hist = sorted(set(inc.columns) | set(bs.columns) | set(cf.columns), reverse=True)[:years]
        if not hist:
            st.info(f'No verified {frequency.lower()} trend data available for this company.')
        else:
            left, right = st.columns(2, gap='medium')
            with left:
                _chart('Revenue & earnings', hist,
                       [(label, [(_value(t_inc, label, p) / 1e9 if _value(t_inc, label, p) is not None else None) for p in hist])
                        for label in ('Revenue', 'Operating income', 'Net income')])
            with right:
                _chart('Profit margins', hist,
                       [(label, [(_ratio(_value(t_inc, numerator, p), _value(t_inc, 'Revenue', p)) * 100
                                  if _ratio(_value(t_inc, numerator, p), _value(t_inc, 'Revenue', p)) is not None else None) for p in hist])
                        for label, numerator in [('Gross margin', 'Gross profit'), ('Operating margin', 'Operating income'), ('Net margin', 'Net income')]], 'percent')
            left, right = st.columns(2, gap='medium')
            with left:
                _chart('Operating & free cash flow', hist,
                       [(label, [(_value(t_cf, label, p) / 1e9 if _value(t_cf, label, p) is not None else None) for p in hist])
                        for label in ('Operating cash flow', 'Free cash flow')])
            with right:
                _chart('Cash & long-term debt', hist,
                       [(label, [(_value(t_bs, label, p) / 1e9 if _value(t_bs, label, p) is not None else None) for p in hist])
                        for label in ('Cash and equivalents', 'Long-term debt')])
        with st.expander('Trend methodology and limitations'):
            st.markdown('Quarterly income and cash-flow observations use 10-Q facts with approximately 65–110 day durations. Balance-sheet facts are point-in-time. Missing Q4 standalone flows are not synthesized from annual reports. The debt line represents **long-term debt**, not total debt. Missing values remain gaps, never zeros. Historical values may be restated in subsequent SEC filings.')
    with tab_summary:
        _card_group('At a glance', [
            ('Revenue', rev, 'money', 'Reported annual revenue'),
            ('Net income', net, 'money', 'Reported annual net income'),
            ('Diluted EPS', eps, 'eps', 'Reported diluted EPS'),
            ('Operating margin', _ratio(op, rev), 'percent', 'Operating income / revenue'),
            ('Free cash flow', fcf, 'money', 'Operating cash flow less capex'),
            ('Revenue growth', _growth(inc, 'Revenue', year_periods), 'percent', 'Previous annual period'),
            ('Cash & equivalents', cash, 'money', 'Period-end cash'),
            ('Long-term debt', debt, 'money', 'Excludes short-term borrowings'),
            ('Return on equity', _ratio(net, equity) if equity is not None and equity > 0 else None, 'percent', 'Period-end equity'),
            ('FCF margin', _ratio(fcf, rev), 'percent', 'Free cash flow / revenue'),
        ])
        st.caption('Explore the tabs for full metrics, valuation assumptions and historical charts. Hover over a tile for its definition.')
    with st.expander('Metric definitions, coverage and limitations'):
        st.markdown('''**Data source:** SEC Company Facts, via the existing project cache. **N/A** means the required fact is missing or a calculation is not safely supported.\n\n**Period alignment:** Point-in-time balance-sheet values and annual income/cash-flow flows are shown for the selected fiscal period end. Growth is meaningful only for comparable consecutive annual periods; verify filing dates before interpreting growth.\n\n**Industry limitations:** Banking, insurance and REIT reporting require specialized indicators. ROIC, debt maturity, full net debt and market valuation remain unavailable until validated input mappings or price feeds are integrated. This page does not generate investment recommendations.''')
