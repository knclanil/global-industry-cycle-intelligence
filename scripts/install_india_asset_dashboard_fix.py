"""Idempotently update dashboard.py to read *canonical* IndiaAssets parquet keys.

Avoid overwriting other dashboards or their newer code.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / 'dashboard.py'
content = path.read_text(encoding='utf-8')
old = 'frames = read_market(market, list(module.TICKERS), start, end)'
new = '''# IndiaAssets uses a virtual G-Sec key that is not in its Yahoo download TICKERS.
    # The scheduled job persists all six canonical symbols, including this key.
    storage_tickers = (
        [*module.SECTORS, module.BENCHMARK]
        if market == "IndiaAssets" else list(module.TICKERS)
    )
    frames = read_market(market, storage_tickers, start, end)'''
if old in content:
    content = content.replace(old, new, 1)
elif 'storage_tickers = (' not in content:
    raise SystemExit('dashboard.py has changed: cannot safely locate price loader. No changes made.')
path.write_text(content, encoding='utf-8')
print('Patched dashboard.py to load all canonical India Asset keys from snapshots.')
