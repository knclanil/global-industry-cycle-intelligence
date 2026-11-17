"""Market-data acquisition, validation and transparent relative rotation metrics."""
from datetime import date, timedelta
import numpy as np
import pandas as pd

SECTORS = {
    'XLC': 'Communication Services', 'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples', 'XLE': 'Energy', 'XLF': 'Financials',
    'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLB': 'Materials',
    'XLRE': 'Real Estate', 'XLK': 'Technology', 'XLU': 'Utilities',
}
TICKERS = list(SECTORS) + ['SPY']
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
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index)).tz_localize(None).normalize()
        frame = frame.sort_index().dropna(how='all')
        if not frame.empty:
            frames[ticker] = frame
    return frames


def validate(frames: dict, requested_end: date) -> dict:
    """Critical integrity checks; benchmark-aligned sessions; nonfatal outlier/freshness checks."""
    errors, warnings = [], []
    required = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    spy = frames.get('SPY')
    if spy is None or spy.empty or 'Close' not in spy:
        return {'status': 'FAIL', 'errors': ['SPY benchmark unavailable'], 'warnings': [], 'latest': None}
    reference = spy['Close'].dropna().index
    if len(reference) < 2:
        return {'status': 'FAIL', 'errors': ['Insufficient SPY sessions'], 'warnings': [], 'latest': None}
    latest = reference.max()
    for ticker in TICKERS:
        df = frames.get(ticker)
        if df is None or df.empty:
            errors.append(f'{ticker}: no data')
            continue
        if not set(required).issubset(df.columns):
            errors.append(f'{ticker}: missing OHLCV / adjusted close columns')
            continue
        if df.index.has_duplicates:
            errors.append(f'{ticker}: duplicate sessions')
        if df[required].isna().any().any():
            errors.append(f'{ticker}: null OHLCV observations')
        if (df[required[:-1]] <= 0).any().any() or (df['Volume'] < 0).any():
            errors.append(f'{ticker}: invalid prices or volume')
        bad = (df['High'] < df[['Open', 'Close', 'Low']].max(axis=1)) | (df['Low'] > df[['Open', 'Close', 'High']].min(axis=1))
        if bad.any():
            errors.append(f'{ticker}: invalid OHLC relationship')
        missing = reference[(reference >= df.index.min()) & (reference <= df.index.max())].difference(df.index)
        if len(missing):
            errors.append(f'{ticker}: {len(missing)} missing benchmark sessions')
        if df.index.max() < latest:
            errors.append(f'{ticker}: missing most recent benchmark session')
        outliers = int((df['Adj Close'].pct_change(fill_method=None).abs() > 0.15).sum())
        if outliers:
            warnings.append(f'{ticker}: {outliers} adjusted-return move(s) > 15%; review corporate actions')
    # Historical queries should not be treated as stale.
    if requested_end >= date.today() - timedelta(days=5) and (pd.Timestamp(requested_end) - latest).days > 5:
        warnings.append(f'Latest observed session is {latest.date()}')
    return {'status': 'FAIL' if errors else 'WARNING' if warnings else 'PASS',
            'errors': errors, 'warnings': warnings, 'latest': latest.date().isoformat()}


def calculate(frames: dict, chosen: list[str], start: date, end: date, lookback: str):
    """Compute an original, zero-centered relative strength/momentum quadrant model.

    RS: sector/SPY ratio return over L sessions.
    Momentum: change in that RS measure over M=max(2,L//2) sessions.
    The momentum change requires L+M warm-up sessions.
    """
    prices = pd.concat({t: df['Adj Close'] for t, df in frames.items()}, axis=1).sort_index()
    prices = prices.loc[:pd.Timestamp(end)].dropna(subset=['SPY'])
    window = prices.loc[pd.Timestamp(start):pd.Timestamp(end)]
    if len(window) < 2:
        raise ValueError('Choose a range containing at least two trading sessions.')
    first, last = window.index[0], window.index[-1]
    L = LOOKBACKS[lookback]
    M = max(2, L // 2)
    ratio = prices.div(prices['SPY'], axis=0)
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
        spy_return = 100 * (prices.at[last, 'SPY'] / prices.at[first, 'SPY'] - 1)
        records.append({'ETF': ticker, 'Sector': SECTORS[ticker], 'Quadrant': status,
                        'Relative strength (%)': round(r, 2), 'RS momentum (pp)': round(m, 2),
                        'Return (%)': round(absolute, 2), 'Excess vs SPY (pp)': round(absolute - spy_return, 2)})
    return pd.DataFrame(records), rs, mom, first, last
