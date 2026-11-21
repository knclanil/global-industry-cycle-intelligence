"""Refresh Yahoo Finance company-sector metadata for the repository's company universe.

Collects DISTINCT company tickers from the source-of-truth holdings datasets and
regional graph edge snapshots (when present). Excludes ETF/index tickers: the
custom source taxonomy remains responsible for those.

Run from anywhere: python scripts/refresh_company_sectors.py
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'dashboard_cache' / 'company_sectors'
OUTPUT_FIELDS = ['Ticker', 'Sector', 'Industry', 'QuoteType', 'Country', 'Company',
                 'Status', 'CheckedUTC', 'Error', 'Source']
COMPANY_TYPES = {'EQUITY', 'COMMON_STOCK'}


def _clean_ticker(value: object, *, india: bool = False) -> str:
    """Normalize whitespace; NSE equity symbols often require a .NS suffix.

    Do not rewrite or guess exotic symbols automatically.
    """
    if pd.isna(value):
        return ''
    value = str(value).strip().upper()
    if not value or value in {'NONE', 'NULL', 'NAN', 'N/A', '-'}:
        return ''
    if india and '.' not in value and not value.startswith('^'):
        value += '.NS'
    return value if re.fullmatch(r'[A-Z0-9^.=\-]+', value) else ''


def collect_universe(root: Path = ROOT) -> pd.DataFrame:
    sources: dict[str, set[str]] = {}

    def add(ticker: object, source: str, *, india: bool = False) -> None:
        t = _clean_ticker(ticker, india=india)
        if t and not t.startswith('^'):
            sources.setdefault(t, set()).add(source)

    # iShares and other ETF holdings: these are underlying company tickers,
    # not the ETF portfolio IDs.
    p = root / 'data' / 'holdings' / 'latest_holdings.parquet'
    if p.exists():
        try:
            data = pd.read_parquet(p, columns=['ticker'])
            for v in data['ticker'].dropna().unique():
                add(v, 'holdings/latest_holdings.parquet')
        except Exception as exc:
            print(f'WARNING: Cannot read {p}: {exc}', file=sys.stderr)

    p = root / 'data' / 'india_holdings' / 'constituents.csv'
    if p.exists():
        try:
            data = pd.read_csv(p, usecols=['symbol'], dtype=str)
            for v in data['symbol'].dropna().unique():
                add(v, 'india_holdings/constituents.csv', india=True)
        except Exception as exc:
            print(f'WARNING: Cannot read {p}: {exc}', file=sys.stderr)

    # The graph might contain companies not represented in latest direct holdings.
    for p in sorted((root / 'data' / 'dashboard_cache' / 'rotation_graphs').glob('*_edges.csv')):
        try:
            data = pd.read_csv(p, usecols=['Ticker'], dtype=str)
            for v in data['Ticker'].dropna().unique():
                add(v, f'rotation_graphs/{p.name}', india=p.name.startswith('india_'))
        except Exception as exc:
            print(f'WARNING: Cannot read {p}: {exc}', file=sys.stderr)

    return pd.DataFrame([{'Ticker': t, 'Source': '; '.join(sorted(src))}
                         for t, src in sorted(sources.items())],
                        columns=['Ticker', 'Source'])


def fetch_one(ticker: str, yf_module, attempts: int = 3, delay: float = 0.5,
              sleep=time.sleep) -> dict:
    """Return metadata without coercing an ETF to a company sector."""
    last_error = ''
    for attempt in range(attempts):
        try:
            info = yf_module.Ticker(ticker).info or {}
            quote_type = str(info.get('quoteType') or '').strip().upper()
            sector = str(info.get('sector') or '').strip()
            industry = str(info.get('industry') or '').strip()
            company = str(info.get('shortName') or info.get('longName') or '').strip()
            country = str(info.get('country') or '').strip()
            # Fund / ETF tickers are not assigned to the 'ETF' company sector.
            if quote_type in {'ETF', 'MUTUALFUND', 'INDEX'}:
                status = 'non_company'
                sector = ''
            elif sector:
                status = 'mapped'
            else:
                status = 'unmapped'
            return {'Ticker': ticker, 'Sector': sector, 'Industry': industry,
                    'QuoteType': quote_type, 'Country': country, 'Company': company,
                    'Status': status, 'Error': ''}
        except Exception as exc:
            last_error = f'{type(exc).__name__}: {str(exc)[:180]}'
            if attempt + 1 < attempts:
                sleep(delay * (2 ** attempt))
    return {'Ticker': ticker, 'Sector': '', 'Industry': '', 'QuoteType': '',
            'Country': '', 'Company': '', 'Status': 'error', 'Error': last_error}


def load_prior(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if not {'Ticker', 'CheckedUTC', 'Status'}.issubset(frame.columns):
            return {}
        return {r['Ticker']: r for r in frame.to_dict('records')}
    except Exception as exc:
        print(f'WARNING: Could not read old cache: {exc}', file=sys.stderr)
        return {}


def is_fresh(row: dict, hours: int, now: datetime) -> bool:
    if not row or row.get('Status') not in {'mapped', 'non_company', 'unmapped'}:
        return False
    try:
        checked = datetime.fromisoformat(row['CheckedUTC'].replace('Z', '+00:00'))
        return now - checked < timedelta(hours=hours)
    except (TypeError, ValueError, KeyError):
        return False


def refresh(root: Path = ROOT, *, max_tickers: int = 0, cache_hours: int = 168,
            delay: float = 0.5, yf_module=None, sleep=time.sleep) -> dict:
    if yf_module is None:
        import yfinance as yf_module
    universe = collect_universe(root)
    if universe.empty:
        raise RuntimeError('No company tickers found in holdings or graph edges. Refresh holdings first.')
    if max_tickers > 0:
        universe = universe.head(max_tickers)
    out = root / 'data' / 'dashboard_cache' / 'company_sectors'
    out.mkdir(parents=True, exist_ok=True)
    output_path = out / 'company_sector_mapping.csv'
    prior = load_prior(output_path)
    now = datetime.now(timezone.utc)
    rows, fetched = [], 0
    for i, row in enumerate(universe.itertuples(index=False), start=1):
        if is_fresh(prior.get(row.Ticker, {}), cache_hours, now):
            record = dict(prior[row.Ticker])
        else:
            record = fetch_one(row.Ticker, yf_module, delay=delay, sleep=sleep)
            record['CheckedUTC'] = datetime.now(timezone.utc).isoformat()
            fetched += 1
            sleep(delay)
        record['Source'] = row.Source
        rows.append({k: record.get(k, '') for k in OUTPUT_FIELDS})
        if i % 100 == 0:
            print(f'Processed {i}/{len(universe)} tickers; fetched {fetched} from Yahoo', flush=True)
            # Checkpoint, so large interrupted jobs retain progress.
            pd.DataFrame(rows, columns=OUTPUT_FIELDS).to_csv(output_path, index=False)
    frame = pd.DataFrame(rows, columns=OUTPUT_FIELDS)
    frame.to_csv(output_path, index=False)
    summary = {'total_tickers': int(len(frame)), 'requested_from_yahoo': fetched,
               'mapped': int(frame.Status.eq('mapped').sum()),
               'unmapped': int(frame.Status.eq('unmapped').sum()),
               'non_company': int(frame.Status.eq('non_company').sum()),
               'errors': int(frame.Status.eq('error').sum()),
               'generated_utc': datetime.now(timezone.utc).isoformat(),
               'file': str(output_path.relative_to(root))}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-tickers', type=int, default=0,
                        help='For testing only (0 = all).')
    parser.add_argument('--cache-hours', type=int, default=168)
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Minimum pause between Yahoo requests; increase if rate limited.')
    args = parser.parse_args()
    refresh(max_tickers=args.max_tickers, cache_hours=args.cache_hours, delay=args.delay)
