"""v3.6.13 | 2026-11-12 | Replace annual line trends with compact bar cards and KPI definitions.
Changelog: v3.6.5 introduced source-aware annual trends; v3.6.13 adds grouped bar charts, definitions and summary deltas.
"""
import math
import pandas as pd
import streamlit as st

METRICS = {
    'Revenue (₹ Cr)': ('Revenue', '₹ Cr'),
    'ROE (%)': ('Return on equity', '%'),
    'Debt/Equity': ('Debt to equity', '×'),
    'Current Ratio': ('Current ratio', '×'),
    'Liabilities / Assets (%)': ('Liabilities / assets', '%'),
    'Equity / Assets (%)': ('Equity / assets', '%'),
    'Operating Margin (%)': ('Operating margin', '%'),
    'Profit Margin (%)': ('Net margin', '%'),
    'Net Income / Cost of Revenue (%)': ('Net income / cost of revenue', '%'),
    'Dividend Yield (%)': ('Dividend yield', '%'),
}


def _number(frame, period, labels):
    if frame is None or frame.empty or period not in frame.columns:
        return None
    for label in labels:
        if label in frame.index:
            value = pd.to_numeric(frame.at[label, period], errors='coerce')
            if pd.notna(value) and math.isfinite(float(value)):
                return float(value)
    return None


def _ratio(num, den, scale=1):
    if num is None or den is None or den <= 0:
        return None
    return num / den * scale


def build_annual_metrics(income, balance, dividends=None, prices=None):
    """Align income and balance sheet on fiscal year; dividend yield uses annual cash dividends / year-end price."""
    periods = sorted(set(getattr(income, 'columns', [])) | set(getattr(balance, 'columns', [])))
    rows = []
    for period in periods:
        date = pd.Timestamp(period)
        revenue = _number(income, period, ['Total Revenue', 'Operating Revenue'])
        net = _number(income, period, ['Net Income', 'Net Income Common Stockholders'])
        op = _number(income, period, ['Operating Income'])
        cost = _number(income, period, ['Cost Of Revenue'])
        equity = _number(balance, period, ['Stockholders Equity', 'Total Equity Gross Minority Interest'])
        assets = _number(balance, period, ['Total Assets'])
        liabilities = _number(balance, period, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
        current_assets = _number(balance, period, ['Current Assets'])
        current_liabilities = _number(balance, period, ['Current Liabilities'])
        debt = _number(balance, period, ['Total Debt'])
        if debt is None:
            long_debt = _number(balance, period, ['Long Term Debt'])
            short_debt = _number(balance, period, ['Current Debt', 'Current Debt And Capital Lease Obligation'])
            if long_debt is not None and short_debt is not None:
                debt = long_debt + short_debt
        div_yield = None
        if dividends is not None and prices is not None and not dividends.empty and not prices.empty:
            # Historical dividend yield: dividends in the trailing 365 days / close on or before fiscal year-end.
            try:
                d = dividends.copy(); p = prices.copy()
                d.index = pd.to_datetime(d.index).tz_localize(None) if d.index.tz is None else pd.to_datetime(d.index).tz_convert(None)
                p.index = pd.to_datetime(p.index).tz_localize(None) if p.index.tz is None else pd.to_datetime(p.index).tz_convert(None)
                ds = d[(d.index > date - pd.Timedelta(days=365)) & (d.index <= date)]
                ps = p[p.index <= date]
                if len(ps) and len(ds):
                    last_close = float(ps.iloc[-1]); annual_div = float(ds.sum())
                    if last_close > 0:
                        div_yield = annual_div / last_close * 100
            except (TypeError, ValueError, AttributeError):
                pass
        rows.append({'Fiscal year': date.year, 'Fiscal period end': date.strftime('%Y-%m-%d'),
                     'Revenue (₹ Cr)': revenue / 1e7 if revenue is not None else None,
                     'ROE (%)': _ratio(net, equity, 100), 'Debt/Equity': _ratio(debt, equity),
                     'Current Ratio': _ratio(current_assets, current_liabilities),
                     'Liabilities / Assets (%)': _ratio(liabilities, assets, 100),
                     'Equity / Assets (%)': _ratio(equity, assets, 100),
                     'Operating Margin (%)': _ratio(op, revenue, 100),
                     'Profit Margin (%)': _ratio(net, revenue, 100),
                     'Net Income / Cost of Revenue (%)': _ratio(net, cost, 100),
                     'Dividend Yield (%)': div_yield})
    return pd.DataFrame(rows).sort_values('Fiscal period end') if rows else pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_annual_history(symbol):
    import yfinance as yf
    ticker = yf.Ticker(symbol.upper() + '.NS')
    income, balance = ticker.income_stmt, ticker.balance_sheet
    dividends = ticker.dividends
    history = ticker.history(period='6y', auto_adjust=False)
    prices = history['Close'] if 'Close' in history else None
    return build_annual_metrics(income, balance, dividends, prices)


KPI_GUIDE = {
    'Revenue (₹ Cr)': ('Total sales recognized during the fiscal year.', 'Total revenue / 10,000,000 to express INR in crore.', 'Revenue growth should be evaluated alongside margins and cash collection.'),
    'ROE (%)': ('Profit generated relative to shareholders’ equity.', 'Net income / period-end shareholders’ equity × 100.', 'High ROE may reflect leverage; compare with debt levels.'),
    'Debt/Equity': ('Borrowings relative to shareholders’ equity.', 'Total debt / shareholders’ equity.', 'Lower leverage is often safer, but norms differ by industry.'),
    'Current Ratio': ('Coverage of short-term liabilities by short-term assets.', 'Current assets / current liabilities.', 'Very high values may also indicate idle working capital.'),
    'Liabilities / Assets (%)': ('Share of assets funded by total liabilities.', 'Total liabilities / total assets × 100.', 'Not the same as interest-bearing debt; compare within industries.'),
    'Equity / Assets (%)': ('Share of assets funded by shareholders’ equity.', 'Shareholders’ equity / total assets × 100.', 'Negative equity can make this measure hard to interpret.'),
    'Operating Margin (%)': ('Operating profit earned per rupee of revenue.', 'Operating income / revenue × 100.', 'Evaluate margin stability across business cycles.'),
    'Profit Margin (%)': ('Net profit earned per rupee of revenue.', 'Net income / revenue × 100.', 'Can be affected by one-off items and taxes.'),
    'Net Income / Cost of Revenue (%)': ('Net profit relative to direct cost of sales; nonstandard measure.', 'Net income / cost of revenue × 100.', 'Not comparable when cost of revenue is absent or classified differently.'),
    'Dividend Yield (%)': ('Historical dividend paid per share relative to fiscal-year-end share price.', 'Trailing 365-day dividends per share / fiscal-year-end closing price × 100.', 'A high yield can result from a falling share price; not a dividend-safety measure.'),
}

KPI_GROUPS = {
    'Revenue & profitability': ['Revenue (₹ Cr)', 'ROE (%)', 'Operating Margin (%)', 'Profit Margin (%)', 'Net Income / Cost of Revenue (%)'],
    'Debt & balance sheet': ['Debt/Equity', 'Current Ratio', 'Liabilities / Assets (%)', 'Equity / Assets (%)'],
    'Shareholder returns': ['Dividend Yield (%)'],
}


# v3.6.14 (2026-11-12): Show concise directional guidance directly in each KPI card.
# These are screening heuristics, not investment recommendations or absolute rules.
KPI_DIRECTION = {
    'Revenue (₹ Cr)': ('🟢 ↑ Good', '🔴 ↓ Bad'),
    'ROE (%)': ('🟢 ↑ Generally good', '🔴 ↓ Generally bad'),
    'Debt/Equity': ('🔴 ↑ Generally bad', '🟢 ↓ Generally good'),
    'Current Ratio': ('🟡 ↑ Depends', '🟡 ↓ Depends'),
    'Liabilities / Assets (%)': ('🔴 ↑ Generally bad', '🟢 ↓ Generally good'),
    'Equity / Assets (%)': ('🟢 ↑ Generally good', '🔴 ↓ Generally bad'),
    'Operating Margin (%)': ('🟢 ↑ Good', '🔴 ↓ Bad'),
    'Profit Margin (%)': ('🟢 ↑ Good', '🔴 ↓ Bad'),
    'Net Income / Cost of Revenue (%)': ('🟢 ↑ Generally good', '🔴 ↓ Generally bad'),
    'Dividend Yield (%)': ('🟡 ↑ Depends', '🟡 ↓ Depends'),
}


def _render_metric_card(df, key):
    import plotly.graph_objects as go
    label, unit = METRICS[key]
    definition, formula, interpretation = KPI_GUIDE[key]
    valid = df[['Fiscal period end', key]].copy()
    valid[key] = pd.to_numeric(valid[key], errors='coerce')
    valid = valid.dropna().sort_values('Fiscal period end')
    with st.container(border=True):
        st.markdown(f'**{label}**')
        st.caption('How to read: ' + '  |  '.join(KPI_DIRECTION[key]))
        if valid.empty:
            st.info('N/A — not reported for available years.')
        else:
            latest = float(valid[key].iloc[-1])
            previous = float(valid[key].iloc[-2]) if len(valid) > 1 else None
            delta = latest - previous if previous is not None else None
            fmt = f'{latest:,.2f} {unit}'
            delta_label = f'{delta:+,.2f} {unit} vs prior year' if delta is not None else 'Only one period available'
            # Neutral deltas: an increase is not always financially favorable.
            st.metric('Latest available', fmt, delta=delta_label, delta_color='off')
            years = pd.to_datetime(valid['Fiscal period end']).dt.strftime('FY%Y').tolist()
            fig = go.Figure(go.Bar(x=years, y=valid[key].tolist(),
                                   text=[f'{v:,.1f}' for v in valid[key]],
                                   textposition='outside', marker_color='#3975B7',
                                   hovertemplate='%{x}<br>%{y:,.2f} ' + unit + '<extra></extra>'))
            fig.update_layout(height=235, margin=dict(l=4, r=8, t=20, b=4),
                              xaxis=dict(title=None, type='category', showgrid=False),
                              yaxis=dict(title=None, zeroline=True, gridcolor='rgba(128,128,128,0.15)'),
                              showlegend=False, bargap=0.35)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='trend_bar_' + key)
        with st.expander('Definition · formula · interpretation'):
            st.markdown(f'**Definition:** {definition}\n\n**Formula:** {formula}\n\n**How to read:** {interpretation}')


def render_india_trends(symbol):
    st.markdown('### Historical trends — 10 financial indicators')
    st.caption('Compact annual bar charts · definitions and formulas · verified available periods only. Source: Yahoo Finance annual statements and dividend/price history; typically around four years.')
    if st.button('Load annual financial trends', key='india_trend_load_' + symbol):
        st.session_state['india_trend_selected'] = symbol
    if st.session_state.get('india_trend_selected') != symbol:
        st.info('Select Load annual financial trends to retrieve historical statements for this company.')
        return
    try:
        with st.spinner('Loading annual financial statements…'):
            df = fetch_annual_history(symbol)
    except Exception as exc:
        st.warning(f'Annual history could not be retrieved: {type(exc).__name__}: {str(exc)[:180]}')
        return
    if df.empty:
        st.warning('The source returned no annual financial statements for this company.')
        return
    st.caption('How to read: 🟢 generally favorable · 🔴 generally unfavorable · 🟡 depends on context. Arrows describe the direction of the KPI, not the stock price. Compare with peers; exceptions apply, especially for banks and negative equity.')
    for group, keys in KPI_GROUPS.items():
        st.markdown(f'#### {group}')
        for index in range(0, len(keys), 2):
            columns = st.columns(2, gap='medium')
            for col, key in zip(columns, keys[index:index + 2]):
                with col:
                    _render_metric_card(df, key)
    st.markdown('#### Historical values and source periods')
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button('Download annual fundamental trends CSV', df.to_csv(index=False).encode(),
                       f'{symbol}_india_fundamental_trends_v3_6_14.csv', 'text/csv')
    st.caption('Financial firms may not report comparable industrial ratios. Missing values are not interpolated. ROE uses period-end equity; net income / cost of revenue is nonstandard. Verify against issuer filings.')
