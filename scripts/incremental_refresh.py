"""Refresh only a market group after its local exchange close.

Usage: python scripts/incremental_refresh.py --region india|us --bootstrap-years 5
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import sys
import traceback
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import stored_market_data as store

REGIONS = {
    'india': ['India', 'IndiaFactors', 'IndiaAssets'],
    'us': ['USA', 'Global', 'Countries', 'GlobalFactors', 'USAFactors', 'GlobalAssets', 'USAAssets'],
}
MODULES = {
    'USA': 'market_data', 'Global': 'global_market_data',
    'Countries': 'country_market_data', 'GlobalFactors': 'global_factor_market_data',
    'USAFactors': 'usa_factor_market_data', 'India': 'india_market_data',
    'IndiaFactors': 'india_factor_market_data', 'GlobalAssets': 'global_asset_market_data',
    'USAAssets': 'usa_asset_market_data', 'IndiaAssets': 'india_asset_market_data',
}


def refresh(region: str, bootstrap_years: int = 5, overlap_days: int = 10, today: date | None = None) -> dict:
    import importlib
    today = today or datetime.now(timezone.utc).date()
    earliest = today - timedelta(days=365 * bootstrap_years + 5)
    status = {'region': region, 'refreshed_utc': datetime.now(timezone.utc).isoformat(), 'markets': {}, 'errors': []}
    for market in REGIONS[region]:
        module = importlib.import_module(MODULES[market])
        # INDIA_ASSET_PIPELINE_CANONICAL_REFRESH
        tickers = ([*module.SECTORS, module.BENCHMARK]
                   if market == 'IndiaAssets' else list(module.TICKERS))
        existing = {t: store.read_one(market, t) for t in tickers}
        # One provider request per market; fetch missing tickers via a full bootstrap window.
        missing = [t for t in tickers if existing[t].empty]
        starts = [existing[t].index.max().date() - timedelta(days=overlap_days) for t in tickers if not existing[t].empty]
        start = earliest if missing or not starts else min(starts)
        start = max(start, earliest) if not missing else earliest
        try:
            incoming = module.download(start, today)
        except Exception as exc:
            status['errors'].append(f'{market}: provider failure: {exc}')
            status['markets'][market] = {'status': 'FAILED', 'error': str(exc)}
            continue
        changed, unchanged, missing_tickers = [], [], []
        sources_path = store.STORE / market / 'sources.json'
        try:
            sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
        except (OSError, ValueError):
            sources = {}
        for ticker in tickers:
            fresh = incoming.get(ticker)
            if fresh is None or fresh.empty:
                missing_tickers.append(ticker)
                continue
            try:
                combined = store.merge(existing[ticker], fresh)
                if combined.empty:
                    missing_tickers.append(ticker)
                    continue
                if not existing[ticker].empty and combined.equals(store.normalize(existing[ticker])):
                    unchanged.append(ticker)
                    continue
                target = store.path_for(market, ticker)
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_suffix('.parquet.tmp')
                combined.to_parquet(tmp, engine='pyarrow', index=True)
                tmp.replace(target)
                sources[ticker] = str(fresh.attrs.get('source', 'Provider via ' + MODULES[market]))
                changed.append(ticker)
            except Exception as exc:
                status['errors'].append(f'{market}/{ticker}: {exc}')
                missing_tickers.append(ticker)
        if changed:
            sources_path.parent.mkdir(parents=True, exist_ok=True)
            sources_path.write_text(json.dumps(sources, indent=2, sort_keys=True) + '\n')
        # Never remove existing history when the provider fails for a ticker.
        status['markets'][market] = {'status': 'PARTIAL' if missing_tickers else 'OK',
            'changed': changed, 'unchanged': unchanged, 'unavailable_this_run': missing_tickers,
            'request_start': start.isoformat(), 'latest_dates': {
                t: (store.read_one(market, t).index.max().date().isoformat()
                    if not store.read_one(market, t).empty else None) for t in tickers}}
        if missing_tickers:
            status['errors'].append(f'{market}: unavailable this run: {", ".join(missing_tickers)}')
    store.STORE.mkdir(parents=True, exist_ok=True)
    (store.STORE / f'refresh_{region}.json').write_text(json.dumps(status, indent=2) + '\n')
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', required=True, choices=REGIONS)
    parser.add_argument('--bootstrap-years', type=int, default=5)
    parser.add_argument('--overlap-days', type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.bootstrap_years <= 15 or not 1 <= args.overlap_days <= 90:
        parser.error('bootstrap-years must be 1..15; overlap-days must be 1..90')
    result = refresh(args.region, args.bootstrap_years, args.overlap_days)
    print(json.dumps(result, indent=2))
    # Fail if any entire market could not be retrieved; partial results are retained.
    sys.exit(1 if any(v['status'] == 'FAILED' for v in result['markets'].values()) else 0)
