"""Repository-backed daily OHLCV snapshots; no network access on cache hits."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'data' / 'market'
FIELDS = ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume')


def path_for(market: str, ticker: str) -> Path:
    # Encode symbols such as ^NSEI without allowing filesystem traversal.
    from urllib.parse import quote
    return STORE / market / (quote(ticker, safe='') + '.parquet')


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=list(FIELDS), index=pd.DatetimeIndex([], name='Date'))
    df = frame.copy()
    ix = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True)).tz_convert(None).normalize()
    df.index = ix
    df.index.name = 'Date'
    df = df.loc[~df.index.duplicated(keep='last')].sort_index()
    for col in FIELDS:
        if col not in df.columns:
            if col == 'Adj Close' and 'Close' in df:
                df[col] = df['Close']
            elif col == 'Volume':
                df[col] = 0
    cols = [c for c in FIELDS if c in df.columns]
    df = df[cols].apply(pd.to_numeric, errors='coerce')
    if 'Adj Close' not in df or df['Adj Close'].dropna().empty:
        raise ValueError('Missing adjusted close')
    df = df.dropna(subset=['Adj Close'])
    df = df[df['Adj Close'] > 0]
    return df


def read_one(market: str, ticker: str) -> pd.DataFrame:
    path = path_for(market, ticker)
    if not path.is_file():
        return pd.DataFrame()
    frame = normalize(pd.read_parquet(path))
    meta_path = STORE / market / 'sources.json'
    if meta_path.is_file():
        try:
            frame.attrs['source'] = json.loads(meta_path.read_text()).get(ticker, 'Stored market data')
        except (ValueError, OSError):
            frame.attrs['source'] = 'Stored market data'
    return frame


def read_market(market: str, tickers: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
    frames = {}
    for ticker in tickers:
        df = read_one(market, ticker)
        if not df.empty:
            window = df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))].copy()
            window.attrs.update(df.attrs)
            if not window.empty:
                frames[ticker] = window
    return frames


def merge(old: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    fresh = normalize(incoming)
    if fresh.empty:
        return normalize(old)
    if old.empty:
        return fresh
    # Newer provider observations replace overlapping stored sessions.
    return normalize(pd.concat([normalize(old), fresh]))
