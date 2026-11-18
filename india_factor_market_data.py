"""India factor indices, primary NSE India historical closes, Yahoo only for verified benchmark equivalent."""
from datetime import date, timedelta
import requests
import pandas as pd
import india_market_data as india
import global_market_data as shared
import market_data as core

SECTORS = {
    'NIFTY50_VALUE20': 'Value (Nifty50 Value 20)',
    'NIFTY200_MOMENTUM30': 'Momentum (Nifty200 Momentum 30)',
    'NIFTY200_QUALITY30': 'Quality (Nifty200 Quality 30)',
    'NIFTY100_LOWVOL30': 'Low Volatility (Nifty100 Low Volatility 30)',
    'NIFTY_ALPHA50': 'Alpha (Nifty Alpha 50)',
    'NIFTY50_EQUALWEIGHT': 'Equal Weight (Nifty50 Equal Weight)',
}
NSE_NAMES = {
    'NIFTY50_VALUE20': 'NIFTY50 VALUE 20',
    'NIFTY200_MOMENTUM30': 'NIFTY200 MOMENTUM 30',
    'NIFTY200_QUALITY30': 'NIFTY200 QUALITY 30',
    'NIFTY100_LOWVOL30': 'NIFTY100 LOW VOLATILITY 30',
    'NIFTY_ALPHA50': 'NIFTY ALPHA 50',
    'NIFTY50_EQUALWEIGHT': 'NIFTY50 EQUAL WEIGHT',
    '^NSEI': 'NIFTY 50',
}
BENCHMARK = '^NSEI'
TICKERS = [*SECTORS, BENCHMARK]
LOOKBACKS = core.LOOKBACKS
QUADRANTS = core.QUADRANTS


def download(start: date, end: date) -> dict[str, pd.DataFrame]:
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
                            'Accept': 'application/json, text/plain, */*', 'Referer': 'https://www.nseindia.com/'})
    frames = {}
    for ticker, name in NSE_NAMES.items():
        try:
            frame = india._nse_history(session, name, start, end)
            if not india._structurally_valid(frame):
                raise ValueError(f'NSE returned invalid OHLC for {name}')
            frame.attrs['source'] = 'NSE India'
            frames[ticker] = frame
        except (requests.RequestException, ValueError, KeyError, TypeError):
            pass
    if BENCHMARK not in frames:
        # ^NSEI is a verified Yahoo Finance representation of Nifty 50.
        yahoo = india._yahoo_history(start, end)
        if BENCHMARK in yahoo:
            frames[BENCHMARK] = yahoo[BENCHMARK]
            frames[BENCHMARK].attrs['source'] = 'Yahoo Finance (benchmark fallback)'
    if not frames:
        raise ValueError('NSE returned no factor index history and Yahoo benchmark unavailable.')
    return frames


def _remap(frames):
    return {('ACWI' if ticker == BENCHMARK else ticker): frame for ticker, frame in frames.items()}


def validate(frames, requested_end):
    # Reuse market benchmark-aligned structural checks, with explicit missing-factor warnings.
    report = shared.validate(_remap(frames), requested_end)
    report['warnings'] = [w.replace('ACWI', 'Nifty 50') for w in report['warnings'] if not any(w.startswith(t + ':') for t in shared.SECTORS)]
    report['errors'] = [e.replace('ACWI', 'Nifty 50') for e in report['errors']]
    for ticker in SECTORS:
        if ticker not in frames:
            report['warnings'].append(f'{ticker}: NSE series unavailable; no verified Yahoo equivalent; excluded')
    if report['status'] != 'FAIL' and report['warnings']:
        report['status'] = 'WARNING'
    return report


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
        raise ValueError('At least two ACWI sessions are required.')
    base = window.iloc[0]
    if base.isna().any() or (base <= 0).any():
        raise ValueError('A selected sector has no valid price on the starting session.')
    cumulative = (window.div(base) - 1) * 100
    trend = cumulative[chosen].sub(cumulative[BENCHMARK], axis=0)
    trend.iloc[0] = 0.0
    return trend
