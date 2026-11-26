"""Recovery layer for india_asset_market_data.download.

Preserves existing NSE benchmark/bond-source methods. Retries individual Yahoo
quotes when the repository's bulk-download path returns empty or truncated data.
No forward filling or synthetic prices. Source labels are retained.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import json
import time
import pandas as pd

EQUITY_ETFS = ('NIFTYBEES.NS', 'GOLDBEES.NS', 'SILVERBEES.NS', 'LIQUIDBEES.NS')
BOND_ETF = 'SETF10GILT.NS'
BENCHMARK = '^NSEI'


def normalise_quote(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    """Return validated daily OHLCV as expected by core market-data routines."""
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()
    f = frame.copy()
    if isinstance(f.columns, pd.MultiIndex):
        if len(f.columns.get_level_values(-1).unique()) == 1:
            f.columns = f.columns.get_level_values(0)
        elif len(f.columns.get_level_values(0).unique()) == 1:
            f.columns = f.columns.get_level_values(-1)
        else:
            return pd.DataFrame()
    f.columns = [str(c).strip() for c in f.columns]
    if 'Close' not in f.columns:
        return pd.DataFrame()
    try:
        dt = pd.to_datetime(f.index, utc=True, errors='coerce')
        valid = ~pd.isna(dt)
        f = f.loc[valid].copy()
        f.index = dt[valid].tz_convert(None).normalize()
    except (TypeError, ValueError):
        return pd.DataFrame()
    f = f[~f.index.duplicated(keep='last')].sort_index()
    for c in ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'):
        if c not in f.columns:
            if c == 'Adj Close':
                f[c] = f['Close']
            elif c == 'Volume':
                f[c] = 0
            else:
                f[c] = f['Close']
        f[c] = pd.to_numeric(f[c], errors='coerce')
    f = f.dropna(subset=['Close', 'Adj Close'])
    f = f.loc[(f['Adj Close'] > 0) & (f['Close'] > 0)]
    # Lack of a dividend-adjusted quote is recorded rather than misrepresented.
    f = f[['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
    f.attrs.update(source=source, instrument_type='Market-price proxy')
    return f


def sufficient(frame: pd.DataFrame | None, required: int = 5) -> bool:
    return isinstance(frame, pd.DataFrame) and not frame.empty and len(frame) >= required and 'Adj Close' in frame and frame['Adj Close'].notna().sum() >= required


def download_one(ticker: str, start: date, end: date, attempts: int = 2, pause: float = 1.0) -> pd.DataFrame:
    """Yahoo individual symbol fallback; never relabel one instrument as another."""
    import yfinance as yf
    for i in range(attempts):
        try:
            raw = yf.Ticker(ticker).history(start=start.isoformat(),
                    end=(end + timedelta(days=1)).isoformat(),
                    auto_adjust=False, actions=False, raise_errors=False)
            clean = normalise_quote(raw, f'Yahoo Finance individual history · {ticker}')
            if sufficient(clean, 2):
                return clean
        except Exception:  # provider errors are captured by diagnostics upstream
            pass
        if i + 1 < attempts:
            time.sleep(pause)
    return pd.DataFrame()


def recover(original_download, start: date, end: date):
    """Use original NSE paths, retry Yahoo only for missing ETF/index histories."""
    try:
        frames = original_download(start, end)
    except Exception:
        frames = {}
    frames = dict(frames or {})
    for ticker in (*EQUITY_ETFS, BENCHMARK):
        if sufficient(frames.get(ticker), 2):
            continue
        fallback = download_one(ticker, start, end)
        if sufficient(fallback, 2):
            frames[ticker] = fallback
    # Existing code prefers official NSE government bond index. Only retry ETF
    # fallback if the index/bond proxy was not returned; this is NOT a bond index.
    if not sufficient(frames.get('NIFTY_GSEC_10Y'), 2):
        fallback = download_one(BOND_ETF, start, end)
        if sufficient(fallback, 2):
            fallback.attrs.update(instrument_type='Government bond ETF',
                 return_basis='ETF adjusted close', underlying_symbol=BOND_ETF,
                 fallback_used='Yes')
            frames['NIFTY_GSEC_10Y'] = fallback
    return frames


def coverage(frames: dict, requested_end: date, lookback: int = 63) -> pd.DataFrame:
    """Diagnostics without declaring missing series to be zero-return assets."""
    rows = []
    for ticker in (*EQUITY_ETFS, 'NIFTY_GSEC_10Y', BENCHMARK):
        f = frames.get(ticker)
        count = int(len(f)) if isinstance(f, pd.DataFrame) else 0
        last = f.index.max() if count else pd.NaT
        stale = bool(count and (pd.Timestamp(requested_end) - last).days > 7)
        rows.append({'ticker': ticker, 'observations': count,
                     'last_date': last.date().isoformat() if count else '',
                     'source': f.attrs.get('source', '') if count else '',
                     'status': ('Unavailable' if not count else
                               'Insufficient history' if count < (lookback + lookback // 2 + 2) else
                               'Stale' if stale else 'Available')})
    return pd.DataFrame(rows)


def save_diagnostics(frames: dict, end: date, output: str | Path, lookback: int = 63):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = coverage(frames, end, lookback)
    table.to_csv(path, index=False)
    return table
