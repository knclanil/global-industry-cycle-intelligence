"""Authoritative India Asset Flow refresh: persist real prices then report coverage.

The dashboard and CI validator read the same canonical snapshots. Never write
fake values, forward-fill missing sessions, or merge bond index with ETF fallback.
"""
from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import india_asset_market_data as asset
from india_asset_recovery import coverage
from stored_market_data import merge, normalize, path_for, read_one, read_market

MARKET = 'IndiaAssets'
SYMBOLS = [*asset.SECTORS, asset.BENCHMARK]
PRICE_DIR = ROOT / 'data' / 'market' / MARKET
COVERAGE = ROOT / 'data' / 'dashboard_cache' / 'india_asset_flow_coverage.csv'


def main(today: date | None = None) -> int:
    today = today or date.today()
    stored_before = {t: read_one(MARKET, t) for t in SYMBOLS}
    # Bootstrap missing series with enough sessions for 12M RS and momentum.
    start = today - timedelta(days=1200 if any(f.empty for f in stored_before.values()) else 60)
    # Repository module already wraps its original download in recovery on main.
    # Do not double-wrap and perform twice the network requests.
    incoming = asset.download(start, today)
    if not isinstance(incoming, dict):
        raise RuntimeError('India asset downloader did not return symbol frames')

    sources_path = PRICE_DIR / 'sources.json'
    try:
        sources = json.loads(sources_path.read_text(encoding='utf-8')) if sources_path.exists() else {}
    except (OSError, ValueError):
        sources = {}
    if not isinstance(sources, dict):
        sources = {}

    changed = []
    for ticker in SYMBOLS:
        frame = incoming.get(ticker)
        if frame is None or frame.empty:
            print(f'WARNING: {ticker}: download unavailable, retaining historical snapshot')
            continue
        cleaned = normalize(frame)
        if cleaned.empty:
            print(f'WARNING: {ticker}: no valid observations')
            continue
        # Never splice a bond price index and an ETF proxy across refreshes.
        # Preserve the existing series until a separate, explicit backfill
        # migration establishes a single consistent source for all dates.
        previous_source = str(sources.get(ticker, ''))
        fresh_source = str(frame.attrs.get('source', ''))
        if ticker == asset.GSEC_KEY and not stored_before[ticker].empty and previous_source:
            previous_is_etf = 'ETF' in previous_source.upper()
            fresh_is_etf = 'ETF' in fresh_source.upper()
            if previous_is_etf != fresh_is_etf:
                print(f'WARNING: {ticker}: provider basis changed; refusing to splice index and ETF history')
                continue
        combined = merge(stored_before[ticker], cleaned)
        target = path_for(MARKET, ticker)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement: never leave a partially written parquet on failure.
        temporary = target.with_suffix('.parquet.tmp')
        try:
            combined.to_parquet(temporary, engine='pyarrow', index=True)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        sources[ticker] = str(frame.attrs.get('source', sources.get(ticker, 'Market data provider')))
        changed.append(ticker)
        print(f'{ticker}: saved {len(combined)} sessions through {combined.index.max().date()}')

    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(json.dumps(sources, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    # Inspect precisely what Streamlit reads, not just what downloader returned.
    persisted = read_market(MARKET, SYMBOLS, today - timedelta(days=1200), today)
    report = coverage(persisted, today, lookback=63)
    COVERAGE.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(COVERAGE, index=False)
    print(report.to_string(index=False))

    if asset.BENCHMARK not in persisted:
        raise RuntimeError('Nifty 50 benchmark missing from persisted snapshot')
    if not any(t in persisted for t in asset.SECTORS):
        raise RuntimeError('No India asset class in persisted snapshots')
    print(f'India Asset Flow snapshots ready: {len(persisted)}/{len(SYMBOLS)} series; updated={changed}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
