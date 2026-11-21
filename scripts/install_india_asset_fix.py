"""Idempotently attach robust ETF history recovery to the existing module."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'india_asset_market_data.py'
START = '# BEGIN INDIA ASSET HISTORY RECOVERY V1'
END = '# END INDIA ASSET HISTORY RECOVERY V1'
APPEND = '''\n\n# BEGIN INDIA ASSET HISTORY RECOVERY V1\n# Keep original NSE government-bond and benchmark precedence unchanged.\nfrom india_asset_recovery import recover as _recover_india_asset_history\n_original_india_asset_download = download\n\ndef download(start, end):\n    return _recover_india_asset_history(_original_india_asset_download, start, end)\n# END INDIA ASSET HISTORY RECOVERY V1\n'''

def install():
    if not TARGET.is_file():
        raise FileNotFoundError(f'Missing original module: {TARGET}')
    if not (ROOT / 'india_asset_recovery.py').is_file():
        raise FileNotFoundError('Copy india_asset_recovery.py into repository root')
    original = TARGET.read_text(encoding='utf-8')
    if START in original:
        print('India Asset Flow recovery is already installed')
        return
    if 'def download(' not in original:
        raise ValueError('Existing module does not expose download(start, end)')
    TARGET.write_text(original.rstrip() + APPEND, encoding='utf-8')
    print('Installed India Asset Flow quote-retry wrapper')

if __name__ == '__main__':
    install()
