"""Market-data acquisition, validation and transparent relative rotation metrics."""
from datetime import date, timedelta
import numpy as np
import pandas as pd

SECTORS = {
    '^NIFTYBANK': 'Banking',
    '^CNXIT': 'Information Technology',
    '^CNXAUTO': 'Automobiles',
    '^CNXFMCG': 'FMCG',
    '^CNXPHARMA': 'Pharmaceuticals',
    '^CNXMETAL': 'Metals',
    '^CNXREALTY': 'Real Estate',
    '^CNXENERGY': 'Energy',
    '^CNXINFRA': 'Infrastructure',
    '^NIFTYFIN_SERVICE': 'Financial Services',
    '^CNXMEDIA': 'Media',
    '^CNXPSUBANK': 'Public Sector Banks',
}
BENCHMARK = '^NSEI'
TICKERS = list(SECTORS) + [BENCHMARK]
LOOKBACKS = {'1W': 5, '2W': 10, '4W': 20, '1M': 21, '3M': 63, '6M': 126, '12M': 252}
QUADRANTS = ('Leading', 'Improving', 'Weakening', 'Lagging')


def download(start: date, end: date) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    raw = yf.download(TICKERS, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                      auto_adjust=False, actions=False, group_by='ticker', threads=True, progress=False)
    if raw.empty:
        raise ValueError('Market-data provider returned no observations.')
    frames = {}
    for ticker in TICKERS:
        if not isinstance(raw.columns, pd.MultiIndex):
            continue
        if ticker in raw.columns.get_level_values(0):
            frame = raw[ticker].copy()
        elif ticker in raw.columns.get_level_values(1):
            frame = raw.xs(ticker, axis=1, level=1).copy()
        else:
            continue
        if 'Adj Close' not in frame.columns and 'Close' in frame.columns:
            frame['Adj Close'] = frame['Close']
        if 'Volume' not in frame.columns and 'Close' in frame.columns:
            frame['Volume'] = 0
        elif 'Volume' in frame.columns:
            frame['Volume'] = frame['Volume'].fillna(0)
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index)).tz_localize(None).normalize()
        frame = frame.sort_index().dropna(how='all')
        if not frame.empty:
            frames[ticker] = frame
    return frames


def validate(frames: dict, requested_end: date) -> dict:
    """Critical integrity checks; benchmark-aligned sessions; nonfatal outlier/freshness checks."""
    errors, warnings = [], []
    required = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    spy = frames.get(BENCHMARK)
    if spy is None or spy.empty or 'Close' not in spy:
        return {'status': 'FAIL', 'errors': ['Nifty 50 benchmark unavailable'], 'warnings': [], 'latest': None}
    reference = spy['Close'].dropna().index
    if len(reference) < 2:
        return {'status': 'FAIL', 'errors': ['Insufficient Nifty 50 sessions'], 'warnings': [], 'latest': None}
    latest = reference.max()
    for ticker in TICKERS:
        df = frames.get(ticker)
        is_benchmark = ticker == BENCHMARK
        if df is None or df.empty:
            (errors if is_benchmark else warnings).append(f'{ticker}: no data from provider; excluded')
            continue
        if not set(required).issubset(df.columns):
            (errors if is_benchmark else warnings).append(f'{ticker}: missing price columns; excluded')
            if not is_benchmark:
                frames.pop(ticker, None)
            continue
        issues = []
        if df.index.has_duplicates:
            issues.append('duplicate sessions')
        # Yahoo frequently returns all-NaN placeholder rows for unavailable index sessions.
        # Discard these; never invent or forward-fill market observations.
        cleaned = df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Adj Close'])
        dropped = len(df) - len(cleaned)
        if dropped:
            warnings.append(f'{ticker}: discarded {dropped} incomplete provider rows')
        if cleaned.empty:
            issues.append('no complete price observations')
        else:
            if (cleaned[required[:-1]] <= 0).any().any() or (cleaned['Volume'] < 0).any():
                issues.append('invalid prices or volume')
            bad = (cleaned['High'] < cleaned[['Open', 'Close', 'Low']].max(axis=1)) | (cleaned['Low'] > cleaned[['Open', 'Close', 'High']].min(axis=1))
            if bad.any():
                issues.append('invalid OHLC relationship')
        if issues:
            (errors if is_benchmark else warnings).append(f'{ticker}: {", ".join(issues)}; ' + ('benchmark invalid' if is_benchmark else 'excluded'))
            if not is_benchmark:
                frames.pop(ticker, None)
            continue
        frames[ticker] = cleaned
        missing = reference[(reference >= cleaned.index.min()) & (reference <= cleaned.index.max())].difference(cleaned.index)
        if len(missing):
            warnings.append(f'{ticker}: {len(missing)} missing benchmark sessions; only matching sessions analyzed')
        if cleaned.index.max() < latest:
            warnings.append(f'{ticker}: missing most recent benchmark session')
        outliers = int((cleaned['Adj Close'].pct_change(fill_method=None).abs() > 0.15).sum())
        if outliers:
            warnings.append(f'{ticker}: {outliers} adjusted-return move(s) > 15%; review provider data')
    # Historical queries should not be treated as stale.
    if requested_end >= date.today() - timedelta(days=5) and (pd.Timestamp(requested_end) - latest).days > 5:
        warnings.append(f'Latest observed session is {latest.date()}')
    return {'status': 'FAIL' if errors else 'WARNING' if warnings else 'PASS',
            'errors': errors, 'warnings': warnings, 'latest': latest.date().isoformat()}


def calculate(frames: dict, chosen: list[str], start: date, end: date, lookback: str):
    """Compute an original, zero-centered relative strength/momentum quadrant model.

    RS: sector/Nifty 50 ratio return over L sessions.
    Momentum: change in that RS measure over M=max(2,L//2) sessions.
    The momentum change requires L+M warm-up sessions.
    """
    prices = pd.concat({t: df['Adj Close'] for t, df in frames.items()}, axis=1).sort_index()
    prices = prices.loc[:pd.Timestamp(end)].dropna(subset=[BENCHMARK])
    window = prices.loc[pd.Timestamp(start):pd.Timestamp(end)]
    if len(window) < 2:
        raise ValueError('Choose a range containing at least two trading sessions.')
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
        status = ('Leading' if m >= 0 else 'Weakening') if r >= 0 else ('Improving' if m >= 0 else 'Lagging')
        absolute = 100 * (prices.at[last, ticker] / prices.at[first, ticker] - 1)
        spy_return = 100 * (prices.at[last, BENCHMARK] / prices.at[first, BENCHMARK] - 1)
        records.append({'ETF': ticker, 'Sector': SECTORS[ticker], 'Quadrant': status,
                        'Relative strength (%)': round(r, 2), 'RS momentum (pp)': round(m, 2),
                        'Return (%)': round(absolute, 2), 'Excess vs SPY (pp)': round(absolute - spy_return, 2)})
    return pd.DataFrame(records), rs, mom, first, last


def relative_trend_from_zero(frames: dict, chosen: list[str], first, last) -> pd.DataFrame:
    """Cumulative adjusted-price return minus Nifty 50 return (percentage points).

    Each series begins at 0 on the first common trading session of the
    selected range. No filling or interpolation of missing prices.
    """
    prices = pd.concat({t: df['Adj Close'] for t, df in frames.items()}, axis=1).sort_index()
    window = prices.loc[pd.Timestamp(first):pd.Timestamp(last), [BENCHMARK, *chosen]]
    window = window.dropna(subset=[BENCHMARK])
    if window.empty or len(window) < 2:
        raise ValueError('At least two Nifty 50 sessions are required for trend comparison.')
    base = window.iloc[0]
    if base.isna().any() or (base <= 0).any():
        raise ValueError('A selected sector has no valid price on the starting session.')
    cumulative = (window.div(base) - 1) * 100
    trend = cumulative[chosen].sub(cumulative[BENCHMARK], axis=0)
    trend.iloc[0] = 0.0
    return trend
