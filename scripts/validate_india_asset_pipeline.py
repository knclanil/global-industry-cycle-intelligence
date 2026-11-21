"""Integration test against the identical stored data API used by Streamlit."""
from pathlib import Path
from datetime import timedelta
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import india_asset_market_data as asset
from stored_market_data import path_for, read_market


def main():
    symbols = [*asset.SECTORS, asset.BENCHMARK]
    for ticker in symbols:
        file = path_for('IndiaAssets', ticker)
        if file.is_file() and file.stat().st_size <= 0:
            raise RuntimeError(f'Empty snapshot: {file}')
    coverage_file = ROOT / 'data/dashboard_cache/india_asset_flow_coverage.csv'
    if not coverage_file.is_file():
        raise RuntimeError('Coverage file missing')
    coverage = pd.read_csv(coverage_file)
    required = {'ticker', 'observations', 'last_date', 'source', 'status'}
    if not required.issubset(coverage.columns):
        raise RuntimeError(f'Coverage columns missing: {required - set(coverage.columns)}')
    if set(symbols) - set(coverage.ticker):
        raise RuntimeError('Coverage report omits canonical asset symbols')

    last = pd.to_datetime(coverage.loc[coverage.ticker == asset.BENCHMARK, 'last_date'], errors='coerce').max()
    if pd.isna(last):
        raise RuntimeError('No valid benchmark observation date')
    end = last.date()
    frames = read_market('IndiaAssets', symbols, end - timedelta(days=1200), end)
    if asset.BENCHMARK not in frames:
        raise RuntimeError('Dashboard storage API cannot load Nifty 50 benchmark')
    if not any(t in frames for t in asset.SECTORS):
        raise RuntimeError('Dashboard storage API cannot load any asset class')
    rows, *_ = asset.calculate(frames, list(asset.SECTORS), end - timedelta(days=365), end, '3M')
    if rows.empty:
        raise RuntimeError('Stored snapshots loaded but no 3M rotation can be calculated')
    print(f'PASS: Streamlit-compatible stored data produces {len(rows)} India Asset Flow rotations')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
