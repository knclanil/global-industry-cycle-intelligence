"""Inspect provider-returned daily observations without changing or filling them."""
from datetime import date, timedelta
import pandas as pd
import market_data, global_market_data, country_market_data, global_factor_market_data
import usa_factor_market_data, india_market_data, india_factor_market_data
import global_asset_market_data, usa_asset_market_data, india_asset_market_data

MARKETS = {
    'Global Sectors': global_market_data, 'Global Countries': country_market_data,
    'Global Factors': global_factor_market_data, 'Global Asset Flow': global_asset_market_data,
    'USA Sector': market_data, 'USA Factors': usa_factor_market_data,
    'USA Asset Flow': usa_asset_market_data, 'India Sector': india_market_data,
    'India Factors': india_factor_market_data, 'India Asset Flow': india_asset_market_data,
}
KEYS = {'Global Sectors': 'Global', 'Global Countries': 'Countries', 'Global Factors': 'GlobalFactors',
        'Global Asset Flow': 'GlobalAssets', 'USA Sector': 'USA', 'USA Factors': 'USAFactors',
        'USA Asset Flow': 'USAAssets', 'India Sector': 'India', 'India Factors': 'IndiaFactors',
        'India Asset Flow': 'IndiaAssets'}
FIELDS = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']


def raw_rows(frames, symbols=None, start=None, end=None):
    """Long-form provider observations; retain duplicates and invalid values for audit."""
    rows = []
    for ticker, frame in frames.items():
        if symbols is not None and ticker not in symbols:
            continue
        if frame is None or frame.empty:
            continue
        df = frame.copy()
        df.insert(0, 'Session', pd.to_datetime(df.index, errors='coerce'))
        df.insert(0, 'Symbol', ticker)
        df.insert(1, 'Source', frame.attrs.get('source', 'Unspecified provider'))
        df.insert(2, 'Instrument type', frame.attrs.get('instrument_type', 'ETF / index proxy'))
        df.insert(3, 'Return basis', frame.attrs.get('return_basis', 'Provider adjusted close'))
        df.insert(4, 'Fallback used', frame.attrs.get('fallback_used', 'No'))
        df.insert(5, 'Underlying symbol', frame.attrs.get('underlying_symbol', ticker))
        df.insert(6, 'Row duplicate', bool(frame.index.has_duplicates))
        # Per-row duplicate indicator, not merely a series-level flag.
        df['Row duplicate'] = frame.index.duplicated(keep=False)
        for field in FIELDS:
            if field not in df:
                df[field] = float('nan')
        prices = df[['Open', 'High', 'Low', 'Close', 'Adj Close']].apply(pd.to_numeric, errors='coerce')
        df['Invalid price'] = prices.isna().any(axis=1) | prices.le(0).any(axis=1)
        df['Invalid OHLC'] = (prices['High'] < prices[['Open', 'Close', 'Low']].max(axis=1)) | (prices['Low'] > prices[['Open', 'Close', 'High']].min(axis=1))
        df['Invalid volume'] = pd.to_numeric(df['Volume'], errors='coerce').lt(0)
        rows.append(df[['Session', 'Symbol', 'Source', 'Instrument type', 'Return basis', 'Fallback used', 'Underlying symbol', *FIELDS, 'Row duplicate', 'Invalid price', 'Invalid OHLC', 'Invalid volume']].reset_index(drop=True))
    if not rows:
        return pd.DataFrame(columns=['Session', 'Symbol', 'Source', 'Instrument type', 'Return basis', 'Fallback used', 'Underlying symbol', *FIELDS, 'Row duplicate', 'Invalid price', 'Invalid OHLC', 'Invalid volume'])
    result = pd.concat(rows, ignore_index=True)
    result['Session'] = pd.to_datetime(result['Session'], errors='coerce')
    if start is not None:
        result = result[result['Session'] >= pd.Timestamp(start)]
    if end is not None:
        result = result[result['Session'] <= pd.Timestamp(end)]
    return result.sort_values(['Symbol', 'Session'], kind='stable').reset_index(drop=True)


def coverage(frames, module, start, end):
    items = []
    for symbol in [*module.SECTORS, module.BENCHMARK]:
        frame = frames.get(symbol)
        if frame is None or frame.empty:
            items.append({'Symbol': symbol, 'Name': 'Benchmark' if symbol == module.BENCHMARK else module.SECTORS[symbol], 'Source': 'Unavailable', 'Instrument type': None, 'Return basis': None, 'Fallback used': None, 'Underlying symbol': None, 'Sessions': 0, 'First': None, 'Last': None, 'Duplicate sessions': None, 'Invalid adjusted closes': None, 'Status': 'MISSING'})
            continue
        idx = pd.to_datetime(frame.index, errors='coerce')
        within = frame.loc[(idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))]
        adj = pd.to_numeric(within['Adj Close'], errors='coerce') if 'Adj Close' in within else pd.Series(dtype=float)
        invalid = int((adj.isna() | adj.le(0)).sum()) if 'Adj Close' in within else len(within)
        dupes = int(within.index.duplicated(keep=False).sum())
        items.append({'Symbol': symbol, 'Name': 'Benchmark' if symbol == module.BENCHMARK else module.SECTORS[symbol], 'Source': frame.attrs.get('source', 'Unspecified provider'), 'Instrument type': frame.attrs.get('instrument_type', 'ETF / index proxy'), 'Return basis': frame.attrs.get('return_basis', 'Provider adjusted close'), 'Fallback used': frame.attrs.get('fallback_used', 'No'), 'Underlying symbol': frame.attrs.get('underlying_symbol', symbol), 'Sessions': len(within), 'First': within.index.min().date().isoformat() if len(within) else None, 'Last': within.index.max().date().isoformat() if len(within) else None, 'Duplicate sessions': dupes, 'Invalid adjusted closes': invalid, 'Status': 'REVIEW' if dupes or invalid else 'AVAILABLE' if len(within) else 'NO ROWS IN RANGE'})
    return pd.DataFrame(items)


def render_data_table():
    import streamlit as st
    from dashboard import prices_cached
    st.title('Data Table · Raw Market Data')
    st.caption('Inspect provider-returned OHLCV and adjusted closes across all ten dashboards. No filling, interpolation, or fabricated observations.')
    with st.container(border=True):
        a, b = st.columns([1.3, 2])
        with a:
            market = st.selectbox('DASHBOARD / MARKET', list(MARKETS))
        with b:
            period = st.date_input('FROM DATE → TO DATE', value=(date.today()-timedelta(days=90), date.today()), min_value=date(2019,1,1), max_value=date.today(), format='MM/DD/YYYY', key='raw_period')
        refresh = st.button('↻ Refresh raw data (clear 1-hour cache)')
    if refresh:
        prices_cached.clear()
        st.rerun()
    if not isinstance(period, tuple) or len(period) != 2 or period[0] >= period[1]:
        st.info('Select a valid From Date and To Date.'); return
    start, end = period
    module = MARKETS[market]
    with st.spinner('Retrieving source observations…'):
        try:
            frames = prices_cached(KEYS[market], start, end)
        except Exception as exc:
            st.error(f'Data retrieval failed: {exc}'); return
    symbols = [*module.SECTORS, module.BENCHMARK]
    selected = st.multiselect('SYMBOLS / INDICES', symbols, default=symbols, format_func=lambda s: f'{s} · {module.SECTORS.get(s, "Benchmark")}')
    st.markdown('#### Data availability & validation')
    summary = coverage(frames, module, start, end)
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.download_button('↓ Download coverage report (CSV)', summary.to_csv(index=False).encode('utf-8'), file_name=f'{KEYS[market]}_coverage.csv', mime='text/csv')
    try:
        report = module.validate(frames, end)
        st.write(f'**Dashboard validation:** {report.get("status", "Unknown")} · Latest session: {report.get("latest", "Unknown")}')
        for issue in report.get('errors', []): st.error(issue)
        with st.expander('Validation warnings', expanded=bool(report.get('warnings'))):
            for issue in report.get('warnings', []): st.warning(issue)
    except Exception as exc:
        st.warning(f'Validation could not complete: {exc}')
    st.markdown('#### Raw daily observations')
    raw = raw_rows(frames, selected, start, end)
    if raw.empty:
        st.warning('No observations available for the selected symbols and dates.'); return
    only_flagged = st.checkbox('Show only flagged rows (duplicates / invalid values)', value=False)
    if only_flagged:
        raw = raw.loc[raw[['Row duplicate', 'Invalid price', 'Invalid OHLC', 'Invalid volume']].any(axis=1)]
    st.caption(f'{len(raw):,} displayed rows · Values are provider-returned data, not independently exchange-verified. Missing series appear in the coverage report.')
    st.dataframe(raw, use_container_width=True, hide_index=True, height=510)
    export = raw.copy()
    export['Session'] = export['Session'].dt.strftime('%Y-%m-%d')
    st.download_button('↓ Download displayed raw data (CSV)', export.to_csv(index=False).encode('utf-8'), file_name=f'{KEYS[market]}_raw_data.csv', mime='text/csv')
    st.caption('Provider libraries may already normalize or discard some upstream rows before this page receives them. A PASS confirms implemented integrity checks, not independent source verification. No database is used.')
