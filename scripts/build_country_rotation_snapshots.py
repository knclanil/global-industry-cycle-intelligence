"""Calculate rotation classifications for tracked country ETFs against ACWI.

Run from the repository root: python scripts/build_country_rotation_snapshots.py
Writes: data/dashboard_cache/rotation_graphs/country_{1m,3m,6m}_rotations.csv
Only valid market observations are classified; gaps remain unclassified.
"""
from __future__ import annotations
import sys
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import country_market_data as cm

PERIODS = {'1m': 21, '3m': 63, '6m': 126}
OUTPUT = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs'


def calculate_snapshots(frames):
    if cm.BENCHMARK not in frames:
        raise RuntimeError('ACWI benchmark is missing: refusing to classify countries')
    data = {}
    for ticker, frame in frames.items():
        if 'Adj Close' in frame.columns:
            s = pd.to_numeric(frame['Adj Close'], errors='coerce')
            s.index = pd.to_datetime(s.index).tz_localize(None) if s.index.tz is not None else pd.to_datetime(s.index)
            data[ticker] = s.sort_index()
    prices = pd.DataFrame(data).sort_index().dropna(subset=[cm.BENCHMARK])
    if prices.empty:
        raise RuntimeError('No benchmark-aligned prices')
    results = {}
    for period, lookback in PERIODS.items():
        momentum_lag = max(2, lookback // 2)
        ratio = prices.div(prices[cm.BENCHMARK], axis=0)
        strength = 100 * (ratio / ratio.shift(lookback) - 1)
        momentum = strength - strength.shift(momentum_lag)
        rows = []
        for ticker, country in cm.SECTORS.items():
            if ticker not in strength.columns:
                continue
            rs, mom = strength[ticker].iloc[-1], momentum[ticker].iloc[-1]
            if not pd.notna(rs) or not pd.notna(mom):
                continue
            quadrant = ('Leading' if mom >= 0 else 'Weakening') if rs >= 0 else ('Improving' if mom >= 0 else 'Lagging')
            rows.append({'ETF': ticker, 'Country': country, 'Quadrant': quadrant,
                         'Relative strength (%)': round(float(rs), 4),
                         'RS momentum (pp)': round(float(mom), 4),
                         'As of': prices.index[-1].date().isoformat()})
        results[period] = pd.DataFrame(rows, columns=['ETF', 'Country', 'Quadrant',
                'Relative strength (%)', 'RS momentum (pp)', 'As of'])
    return results


def main():
    end = date.today()
    frames = cm.download(end - timedelta(days=540), end)
    results = calculate_snapshots(frames)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for period, data in results.items():
        target = OUTPUT / f'country_{period}_rotations.csv'
        data.to_csv(target, index=False)
        print(f'{target.relative_to(ROOT)}: {len(data)}/{len(cm.SECTORS)} classified')
    if all(df.empty for df in results.values()):
        raise RuntimeError('Country snapshot builder produced no valid classifications')


if __name__ == '__main__':
    main()
