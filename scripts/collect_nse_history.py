"""Official NSE index history ingestion. No fabricated or proxy prices.

Uses NSE's public historical index JSON endpoint when permitted. Accepts manually
exported official CSV files in imports/nse/ as a reliable fallback. No bypasses
of access controls. Existing validated history is preserved on network failure.
"""
import argparse
import io
import json
import os
import random
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
URL = 'https://www.nseindia.com/api/historical/indicesHistory'
COLUMNS = ['date', 'index', 'open', 'high', 'low', 'close', 'source']


def normalize(frame, expected=None, source='NSE official'):
    if frame is None or frame.empty:
        return pd.DataFrame(columns=COLUMNS)
    aliases = {
        'date': ['date', 'eod_timestamp', 'historicaldate', 'timestamp', 'index date', 'index_date'],
        'index': ['index', 'index_name', 'index name', 'indexname', 'historicalindexname'],
        'open': ['open', 'eod_open_index_val', 'opening index value', 'historicalopen'],
        'high': ['high', 'eod_high_index_val', 'high index value', 'historicalhigh'],
        'low': ['low', 'eod_low_index_val', 'low index value', 'historicallow'],
        'close': ['close', 'eod_close_index_val', 'closing index value', 'historicalclose', 'index close'],
    }
    lookup = {re.sub(r'[^a-z0-9]+', '_', str(c).strip().lower()).strip('_'): c for c in frame.columns}
    out = pd.DataFrame(index=frame.index)
    for key, options in aliases.items():
        match = next((lookup[re.sub(r'[^a-z0-9]+', '_', x.lower()).strip('_')] for x in options if re.sub(r'[^a-z0-9]+', '_', x.lower()).strip('_') in lookup), None)
        if match is not None:
            out[key] = frame[match]
    if 'date' not in out or 'close' not in out:
        raise ValueError('Missing required date/close columns: ' + ', '.join(map(str, frame.columns)))
    if 'index' not in out:
        if expected is None:
            raise ValueError('Index name missing; specify index via filename matching watchlist')
        out['index'] = expected
    out['index'] = out['index'].astype(str).str.strip().str.upper()
    if expected:
        # Never attribute another index's data to the requested index.
        out = out[out['index'] == expected.upper()]
    out['date'] = pd.to_datetime(out['date'], errors='coerce', dayfirst=True).dt.strftime('%Y-%m-%d')
    for col in ('open', 'high', 'low', 'close'):
        out[col] = pd.to_numeric(out[col].astype(str).str.replace(',', '', regex=False), errors='coerce') if col in out else float('nan')
    out = out.dropna(subset=['date', 'close'])
    out = out[(out.close > 0) & (out.date <= date.today().isoformat())]
    out['source'] = source
    return out[COLUMNS].drop_duplicates(['index', 'date'], keep='last')


def unpack(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ('data', 'indexCloseOnlineRecords', 'indexData', 'records', 'historical'):
            val = payload.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                result = unpack(val)
                if result:
                    return result
    return []


def fetch(session, name, start, end):
    params = {'indexType': name, 'from': start.strftime('%d-%m-%Y'), 'to': end.strftime('%d-%m-%Y')}
    response = session.get(URL, params=params, timeout=30, headers={'Referer': 'https://www.nseindia.com/reports-indices-historical-index-data', 'Accept': 'application/json'})
    response.raise_for_status()
    if 'json' not in response.headers.get('Content-Type', '').lower():
        raise ValueError('NSE did not return JSON (access restrictions or page response)')
    rows = unpack(response.json())
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return normalize(pd.DataFrame(rows), expected=name, source='NSE historical API')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--years', type=int, default=20)
    parser.add_argument('--mode', choices=['backfill', 'daily', 'import'], default='daily')
    parser.add_argument('--index', help='Only one index name, e.g. NIFTY IT')
    parser.add_argument('--max-requests', type=int, default=0, help='Optional limit for initial testing')
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    names = pd.read_csv(ROOT / 'config/nse_indices.csv')['index_name'].str.upper().tolist()
    if 'NIFTY 50' not in names:
        names.insert(0, 'NIFTY 50')
    if args.index:
        names = [n for n in names if n == args.index.upper()]
        if not names:
            raise SystemExit('Index not found in watchlist')
    dest = DATA / 'nse_index_history.parquet'
    old = pd.read_parquet(dest) if dest.exists() else pd.DataFrame(columns=COLUMNS)
    pieces = [old]
    errors = []
    count = 0
    imported = 0
    # Manually downloaded CSVs from official NSE historical data UI.
    for path in sorted((ROOT / 'imports/nse').glob('*.csv')):
        try:
            raw = pd.read_csv(path, encoding='utf-8-sig')
            slug = path.stem.upper().replace('_', ' ').replace('-', ' ')
            expected = next((n for n in names if n == slug), None)
            part = normalize(raw, expected=expected, source='NSE manual official CSV: ' + path.name)
            part = part[part['index'].isin(names)]
            if len(part):
                pieces.append(part)
                imported += len(part)
        except Exception as exc:
            errors.append({'file': str(path), 'error': str(exc)})
    if args.mode != 'import':
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; historical-index-research/1.0)', 'Accept-Language': 'en-US,en;q=0.9'})
        try:
            session.get('https://www.nseindia.com/', timeout=15)
        except requests.RequestException:
            pass
        end = date.today()
        earliest = end - timedelta(days=round(365.25 * args.years))
        for name in names:
            existing = old[old['index'] == name] if not old.empty else pd.DataFrame()
            if args.mode == 'daily' and not existing.empty:
                start = max(earliest, date.fromisoformat(existing['date'].max()) - timedelta(days=7))
            elif args.mode == 'daily':
                # A new index is backfilled on first run, even in daily mode.
                start = max(earliest, end - timedelta(days=90))
            else:
                start = earliest
            cursor = start
            while cursor <= end:
                if args.max_requests and count >= args.max_requests:
                    break
                stop = min(end, cursor + timedelta(days=89))
                try:
                    part = fetch(session, name, cursor, stop)
                    if not part.empty:
                        pieces.append(part)
                    print(f'{name}: {cursor} to {stop}: {len(part)} rows', flush=True)
                except (requests.RequestException, ValueError, KeyError) as exc:
                    errors.append({'index': name, 'from': str(cursor), 'to': str(stop), 'error': str(exc)})
                    print(f'FAILED {name} {cursor}: {exc}', flush=True)
                    # Do not repeatedly hit a blocked endpoint.
                    if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code in (401, 403, 429):
                        break
                count += 1
                cursor = stop + timedelta(days=1)
                time.sleep(0.25)
            if args.max_requests and count >= args.max_requests:
                break
    combined = pd.concat(pieces, ignore_index=True)
    if not combined.empty:
        combined['date'] = combined['date'].astype(str)
        combined = combined.drop_duplicates(['index', 'date'], keep='last').sort_values(['index', 'date'])
        combined.to_parquet(dest, index=False)
    coverage = []
    for name in names:
        x = combined[combined['index'] == name] if not combined.empty else pd.DataFrame()
        coverage.append({'index': name, 'observations': len(x), 'first_date': x.date.min() if len(x) else None, 'last_date': x.date.max() if len(x) else None})
    (DATA / 'nse_history_coverage.json').write_text(json.dumps({'checked_utc': datetime.now(timezone.utc).isoformat(), 'rows': len(combined), 'imported_rows': imported, 'requests': count, 'coverage': coverage, 'errors': errors[:250]}, indent=2))
    print(f'Total validated historical rows: {len(combined)}; errors: {len(errors)}')
    if combined.empty:
        raise SystemExit('No historical rows available. NSE may restrict automated access. Import official CSVs into imports/nse/.')

if __name__ == '__main__':
    main()
