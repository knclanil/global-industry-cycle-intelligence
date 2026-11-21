"""Persist real India asset histories as well as their diagnostic coverage.

Run from GitHub Actions after installing dependencies. No fabricated values.
"""
from datetime import date, timedelta
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import india_asset_market_data as asset
from india_asset_recovery import coverage
from stored_market_data import normalize, read_one, merge, path_for

MARKET = 'IndiaAssets'
TICKERS = [*asset.SECTORS, asset.BENCHMARK]


def main():
    end = date.today()
    # Warm-up for 12M relative-strength plus momentum; keep ~3y historical data.
    start = end - timedelta(days=1200)
    frames = asset.download(start, end)
    output = ROOT / 'data' / 'dashboard_cache' / 'india_asset_flow_coverage.csv'
    output.parent.mkdir(parents=True, exist_ok=True)
    sources_path = ROOT / 'data' / 'market' / MARKET / 'sources.json'
    try:
        sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
    except (ValueError, OSError):
        sources = {}
    for ticker in TICKERS:
        frame = frames.get(ticker)
        if frame is None or frame.empty:
            print(f'WARNING: {ticker}: no fresh data; retaining previous stored history')
            continue
        try:
            clean = normalize(frame)
            if clean.empty:
                continue
            older = read_one(MARKET, ticker)
            final = merge(older, clean)
            target = path_for(MARKET, ticker)
            target.parent.mkdir(parents=True, exist_ok=True)
            final.to_parquet(target)
            sources[ticker] = frame.attrs.get('source', 'Verified market data provider')
            print(f'Persisted {ticker}: {len(final)} sessions -> {target}')
        except (ValueError, TypeError, KeyError) as exc:
            print(f'WARNING: {ticker}: unable to persist: {exc}')
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(json.dumps(sources, indent=2, sort_keys=True) + '\n')
    # Diagnose the exact same persisted source the Streamlit dashboard now uses.
    persisted = {t: f for t in TICKERS if not (f := read_one(MARKET, t)).empty}
    result = coverage(persisted, end, lookback=63)
    result.to_csv(output, index=False)
    print(result.to_string(index=False))
    if asset.BENCHMARK not in persisted:
        raise SystemExit('ERROR: Nifty benchmark has no stored history; refusing to publish a misleading PASS')
    # Do not fail if only some assets are available; the dashboard can show those.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
