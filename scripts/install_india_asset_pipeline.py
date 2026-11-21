"""One-time, idempotent source integration. Run in CI before generating snapshots.

Only changes two exact source lines in existing repository files. Fails closed
if upstream implementation has changed instead of overwriting custom edits.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def patch(path: Path, old: str, new: str, marker: str) -> None:
    source = path.read_text(encoding='utf-8')
    if marker in source:
        print(f'Already integrated: {path.name}')
        return
    n = source.count(old)
    if n != 1:
        raise SystemExit(f'Expected one integration anchor in {path.name}; found {n}. No changes made.')
    path.write_text(source.replace(old, new, 1), encoding='utf-8')
    print(f'Integrated: {path.name}')


def main() -> None:
    # The original IndiaAssets.TICKERS holds Yahoo download tickers, including the
    # G-Sec ETF fallback, but the canonical stored keys include NIFTY_GSEC_10Y.
    patch(ROOT / 'dashboard.py',
          'frames = read_market(market, list(module.TICKERS), start, end)',
          '''# INDIA_ASSET_PIPELINE_CANONICAL_READ
    storage_symbols = ([*module.SECTORS, module.BENCHMARK]
                       if market == 'IndiaAssets' else list(module.TICKERS))
    frames = read_market(market, storage_symbols, start, end)''',
          'INDIA_ASSET_PIPELINE_CANONICAL_READ')
    patch(ROOT / 'scripts/incremental_refresh.py',
          'tickers = list(module.TICKERS)',
          '''# INDIA_ASSET_PIPELINE_CANONICAL_REFRESH
        tickers = ([*module.SECTORS, module.BENCHMARK]
                   if market == 'IndiaAssets' else list(module.TICKERS))''',
          'INDIA_ASSET_PIPELINE_CANONICAL_REFRESH')


if __name__ == '__main__':
    main()
