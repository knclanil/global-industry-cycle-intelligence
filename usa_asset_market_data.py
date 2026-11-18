"""Cross-asset price-rotation proxies; NOT verified investor fund flows."""
from datetime import date, timedelta
import pandas as pd
import market_data as core
from india_market_data import _clean_provider_rows

SECTORS = {'VTI': 'Equities · US', 'IEF': 'Government Bonds', 'TLT': 'Long Treasury Bonds', 'LQD': 'Investment Grade Credit', 'HYG': 'High Yield Credit', 'GLD': 'Gold', 'DBC': 'Commodities', 'VNQ': 'Real Estate', 'SGOV': 'Cash / Treasury Bills'}
BENCHMARK = 'SPY'
TICKERS = [*SECTORS, BENCHMARK]
LOOKBACKS = core.LOOKBACKS
QUADRANTS = core.QUADRANTS


def download(start: date, end: date) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    raw = yf.download(TICKERS, start=start.isoformat(),
                      end=(end + timedelta(days=1)).isoformat(),
                      auto_adjust=False, actions=False, group_by='ticker',
                      threads=True, progress=False)
    if raw.empty:
        raise ValueError('Cross-asset ETF market-data provider returned no observations.')
    frames = {}
    for ticker in TICKERS:
        if isinstance(raw.columns, pd.MultiIndex):
            if ticker in raw.columns.get_level_values(0):
                frame = raw[ticker].copy()
            elif ticker in raw.columns.get_level_values(1):
                frame = raw.xs(ticker, axis=1, level=1).copy()
            else:
                continue
        elif len(TICKERS) == 1:
            frame = raw.copy()
        else:
            continue
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index)).tz_localize(None).normalize()
        frame = _clean_provider_rows(frame.sort_index().dropna(how='all'))
        if not frame.empty:
            frames[ticker] = frame
    return frames


def _to_core(frames):
    return {('SPY' if ticker == BENCHMARK else ticker): frame for ticker, frame in frames.items()}


def validate(frames: dict, requested_end: date) -> dict:
    # The benchmark is mandatory; individual unavailable sectors are warnings.
    mapped = _to_core(frames)
    if 'SPY' not in mapped:
        return {'status': 'FAIL', 'errors': ['SPY benchmark unavailable'],
                'warnings': [], 'latest': None}
    return _validate_global(mapped, requested_end)


def _validate_global(mapped, requested_end):
    errors, warnings = [], []
    benchmark = mapped.get('SPY')
    if benchmark is None or benchmark.empty or 'Adj Close' not in benchmark:
        return {'status': 'FAIL', 'errors': ['SPY benchmark unavailable or invalid'], 'warnings': [], 'latest': None}
    ref = benchmark['Adj Close'].dropna()
    if len(ref) < 2 or (ref <= 0).any() or ref.index.has_duplicates:
        return {'status': 'FAIL', 'errors': ['SPY benchmark history is invalid'], 'warnings': [], 'latest': None}
    latest = ref.index.max()
    required = {'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'}
    for ticker in TICKERS:
        key = 'SPY' if ticker == BENCHMARK else ticker
        df = mapped.get(key)
        if df is None or df.empty:
            warnings.append(f'{ticker}: unavailable; excluded from calculations')
            continue
        if not required.issubset(df.columns):
            if ticker == BENCHMARK: errors.append('SPY: missing required OHLCV fields')
            else: warnings.append(f'{ticker}: missing required OHLCV fields; excluded')
            continue
        if df.index.has_duplicates or df['Adj Close'].isna().any() or (df['Adj Close'] <= 0).any():
            if ticker == BENCHMARK: errors.append('SPY: duplicate sessions or invalid adjusted closes')
            else: warnings.append(f'{ticker}: invalid prices or dates; excluded')
        if df.index.max() < latest:
            warnings.append(f'{ticker}: latest data older than benchmark')
        missing = ref.index[(ref.index >= df.index.min()) & (ref.index <= df.index.max())].difference(df.index)
        if len(missing): warnings.append(f'{ticker}: {len(missing)} missing SPY sessions')
        if (df['Adj Close'].pct_change(fill_method=None).abs() > 0.15).any():
            warnings.append(f'{ticker}: adjusted daily return exceeds 15%; review')
    if requested_end >= date.today() - timedelta(days=5) and (pd.Timestamp(requested_end) - latest).days > 5:
        warnings.append(f'Latest SPY session is {latest.date()}')
    return {'status': 'FAIL' if errors else 'WARNING' if warnings else 'PASS',
            'errors': errors, 'warnings': warnings, 'latest': latest.date().isoformat()}


def calculate(frames, chosen, start, end, lookback):
    prices = pd.concat({t: df['Adj Close'] for t, df in frames.items() if 'Adj Close' in df and not df['Adj Close'].isna().any() and (df['Adj Close'] > 0).all() and not df.index.has_duplicates}, axis=1).sort_index()
    prices = prices.loc[:pd.Timestamp(end)].dropna(subset=[BENCHMARK])
    window = prices.loc[pd.Timestamp(start):pd.Timestamp(end)]
    if len(window) < 2:
        raise ValueError('Choose at least two trading sessions.')
    first, last = window.index[0], window.index[-1]
    L = LOOKBACKS[lookback]
    M = max(2, L // 2)
    ratio = prices.div(prices[BENCHMARK], axis=0)
    rs = 100 * (ratio / ratio.shift(L) - 1)
    mom = rs - rs.shift(M)
    records = []
    for ticker in chosen:
        if ticker not in prices or pd.isna(rs.at[last, ticker]) or pd.isna(mom.at[last, ticker]):
            continue
        if pd.isna(prices.at[first, ticker]) or pd.isna(prices.at[last, ticker]):
            continue
        r, m = float(rs.at[last, ticker]), float(mom.at[last, ticker])
        quadrant = ('Leading' if m >= 0 else 'Weakening') if r >= 0 else ('Improving' if m >= 0 else 'Lagging')
        absolute = 100 * (prices.at[last, ticker] / prices.at[first, ticker] - 1)
        bench_return = 100 * (prices.at[last, BENCHMARK] / prices.at[first, BENCHMARK] - 1)
        records.append({'ETF': ticker, 'Sector': SECTORS[ticker], 'Quadrant': quadrant,
                        'Relative strength (%)': round(r, 2), 'RS momentum (pp)': round(m, 2),
                        'Return (%)': round(absolute, 2),
                        'Excess vs SPY (pp)': round(absolute - bench_return, 2)})
    return pd.DataFrame(records, columns=['ETF', 'Sector', 'Quadrant', 'Relative strength (%)', 'RS momentum (pp)', 'Return (%)', 'Excess vs SPY (pp)']), rs, mom, first, last


def relative_trend_from_zero(frames, chosen, first, last):
    prices = pd.concat({t: df['Adj Close'] for t, df in frames.items() if 'Adj Close' in df and not df['Adj Close'].isna().any() and (df['Adj Close'] > 0).all() and not df.index.has_duplicates}, axis=1).sort_index()
    window = prices.loc[pd.Timestamp(first):pd.Timestamp(last), [BENCHMARK, *chosen]].dropna(subset=[BENCHMARK])
    if len(window) < 2:
        raise ValueError('At least two SPY sessions are required.')
    base = window.iloc[0]
    if base.isna().any() or (base <= 0).any():
        raise ValueError('A selected sector has no valid price on the starting session.')
    cumulative = (window.div(base) - 1) * 100
    trend = cumulative[chosen].sub(cumulative[BENCHMARK], axis=0)
    trend.iloc[0] = 0.0
    return trend
