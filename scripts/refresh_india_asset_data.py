"""Check each India asset, write readable coverage without forcing false signals."""
from datetime import date, timedelta
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import india_asset_market_data as asset
from india_asset_recovery import save_diagnostics


def main():
    end = date.today()
    start = end - timedelta(days=500)
    frames = asset.download(start, end)
    result = save_diagnostics(frames, end,
        ROOT / 'data/dashboard_cache/india_asset_flow_coverage.csv', lookback=63)
    print(result.to_string(index=False))
    available = result.loc[(result['ticker'] != '^NSEI') & (result['status'] == 'Available')]
    print(f'Usable asset proxies: {len(available)}/5')
    if not len(available):
        print('WARNING: no usable asset price histories; inspect coverage CSV and provider logs.')
    # A successful diagnostic run does not claim pricing success.
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
