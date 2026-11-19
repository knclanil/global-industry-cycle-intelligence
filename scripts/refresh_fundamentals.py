"""Batch SEC filing refresh for verified ETF issuers. Run after holdings refresh.

SEC_USER_AGENT must identify the operator with a real contact address.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fundamental_intelligence as fi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=250)
    parser.add_argument('--delay', type=float, default=0.18)
    args = parser.parse_args()
    universe = fi.load_universe()
    if universe.empty:
        print('No verified holdings snapshot. Run holdings refresh first.')
        return 0
    try:
        directory = fi.company_directory()
    except Exception as exc:
        print(f'SEC directory retrieval failed: {exc}', file=sys.stderr)
        return 1
    fi.STORE.mkdir(parents=True, exist_ok=True)
    (fi.STORE/'sec_company_directory.json').write_text(directory.to_json(orient='records'))
    # Refresh the directory before resolving issuer identities; persist it for the UI.
    result = fi.refresh_us(universe, max_companies=args.limit, directory=directory, delay=args.delay)
    result['as_of_utc'] = datetime.now(timezone.utc).isoformat()
    result['universe_issuers'] = int(universe.issuer_id.nunique())
    result['cached_sec_facts'] = len(list(fi.STORE.glob('facts_*.json')))
    (fi.STORE/'refresh_status.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if not result['errors'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
