#!/usr/bin/env python3
"""Refresh verified NSE-universe company financials via Yahoo Finance.

This batch job is the ONLY component that contacts Yahoo. Streamlit reads
persisted, individually keyed company snapshots for fast page loading.

  python scripts/refresh_india_financials.py --limit 0   # all verified NSE issuers
  python scripts/refresh_india_financials.py --symbols RELIANCE,TCS,INFY --force
  python scripts/refresh_india_financials.py --rebuild-only

Screener.in consolidated reports are provided as per-company research links;
its published terms do not authorize republishing the source's entire data
without permission. No hidden automated Screener scraping occurs here.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from india_financial_data import (
    DATA, AGGREGATE_FIELDS, aggregate_member_financials, company_file, load_company,
    normalize_yahoo_statements, now_utc, safe_symbol, yahoo_symbol, screener_url, summary_row, statement_coverage,
)

COMPANIES_CSV = ROOT / "data" / "india_holdings" / "companies.csv"
SUMMARY_FIELDS = [
    "company_key", "symbol", "company_name", "isin", "industry", "sector", "yahoo_ticker",
    "financial_currency", "quote_currency", "financial_period", "income_period", "balance_period",
    "cashflow_period", "quote_asof", "retrieved_utc", "available_key_metrics",
    "revenue", "net_income", "diluted_eps", "gross_margin", "operating_margin", "net_margin",
    "roe", "roa", "revenue_yoy", "earnings_yoy", "revenue_3y_cagr", "revenue_5y_cagr",
    "operating_cash_flow", "free_cash_flow", "fcf_margin", "total_assets", "total_liabilities",
    "equity", "cash", "total_debt", "net_debt", "current_ratio", "debt_to_equity",
    "cash_conversion", "book_value_per_share", "tangible_book_per_share", "graham_number",
    "market_cap", "price", "pe", "pb", "fcf_yield", "enterprise_value", "ev_to_ebitda",
]
STATUS_FIELDS = ["company_key", "symbol", "company_name", "status", "details", "asof_utc", "snapshot_utc"]


def _atomic_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('wb', delete=False, dir=path.parent, prefix='.pending-') as tmp:
        tmp.write(data)
        pending = Path(tmp.name)
    os.replace(pending, path)


def _atomic_json(path: Path, data: dict):
    _atomic_bytes(path, (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))


def _atomic_csv(path: Path, rows: list[dict], columns: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', delete=False, newline='', encoding='utf-8', dir=path.parent, prefix='.pending-') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
        pending = Path(f.name)
    os.replace(pending, path)


def _read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def fetch_yahoo_company(company: dict) -> dict:
    """Request only the intended `.NS` security. Never guess alternate symbols."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError('yfinance not installed; run pip install -r requirements.txt') from exc
    sym = safe_symbol(company['symbol'])
    ticker_name = yahoo_symbol(sym)
    t = yf.Ticker(ticker_name)
    sheets = {}
    requests = (
        ('annual_income', 'get_income_stmt', 'yearly'),
        ('annual_balance', 'get_balance_sheet', 'yearly'),
        ('annual_cashflow', 'get_cashflow', 'yearly'),
        ('quarterly_income', 'get_income_stmt', 'quarterly'),
        ('quarterly_balance', 'get_balance_sheet', 'quarterly'),
        ('quarterly_cashflow', 'get_cashflow', 'quarterly'),
    )
    errors = []
    for key, method, frequency in requests:
        try:
            sheets[key] = getattr(t, method)(freq=frequency)
        except Exception as exc:
            sheets[key] = None
            errors.append(f'{key}: {type(exc).__name__}: {str(exc)[:90]}')
    statement_data = normalize_yahoo_statements(
        *(sheets[name] for name in ('annual_income', 'annual_balance', 'annual_cashflow',
                                    'quarterly_income', 'quarterly_balance', 'quarterly_cashflow')))
    coverage = statement_coverage({'statements': statement_data}, 'annual')
    quarterly_coverage = statement_coverage({'statements': statement_data}, 'quarterly')
    if not (coverage['best_periods'] or quarterly_coverage['best_periods']):
        raise RuntimeError('Yahoo returned no core income, balance-sheet or cash-flow metrics (even if ancillary rows exist). '
                           + '; '.join(errors[:3]))
    if not any(statement_data['annual'].values()) and not any(statement_data['quarterly'].values()):
        raise RuntimeError('Yahoo returned no usable annual or quarterly financial statements; ' + '; '.join(errors[:2]))
    info = {}
    try:
        info = t.get_info() or {}
    except Exception as exc:
        errors.append(f'company metadata: {type(exc).__name__}: {str(exc)[:90]}')
    published_ticker = str(info.get('symbol') or '').upper()
    if published_ticker and published_ticker != ticker_name:
        raise RuntimeError(f'Yahoo ticker mismatch: requested {ticker_name}, received {published_ticker}')
    q = {}
    try:
        f = t.get_fast_info()
        for name in ('last_price', 'market_cap', 'currency', 'shares'):
            try:
                q[name] = f.get(name) if hasattr(f, 'get') else getattr(f, name)
            except Exception:
                pass
    except Exception as exc:
        errors.append(f'quote: {type(exc).__name__}: {str(exc)[:80]}')
    def positive_float(value):
        try:
            v = float(value)
            return v if v > 0 and v < float('inf') else None
        except (ValueError, TypeError):
            return None
    quote = {
        'price': positive_float(q.get('last_price') or info.get('currentPrice')),
        'market_cap': positive_float(q.get('market_cap') or info.get('marketCap')),
        'shares_outstanding': positive_float(q.get('shares') or info.get('sharesOutstanding')),
        'currency': str(q.get('currency') or info.get('currency') or '').upper(),
        # This is retrieval time, not the official exchange trade timestamp.
        'asof_utc': now_utc(),
        'provenance': 'yahoo_finance_quote_snapshot',
    }
    return {
        'schema_version': 1, 'company_key': company['company_key'],
        'symbol': sym, 'company_name': str(info.get('longName') or info.get('shortName') or company['company_name']),
        'isin': company.get('isin', ''), 'industry': company.get('industry', ''),
        'sector': str(info.get('sector') or ''), 'yahoo_ticker': ticker_name,
        'currency': str(info.get('financialCurrency') or '').upper(),
        'quote': quote, 'statements': statement_data,
        'retrieved_utc': now_utc(),
        'source_urls': {
            'yahoo': f'https://finance.yahoo.com/quote/{ticker_name}/financials/',
            'screener_consolidated_reference': screener_url(sym),
            'nse_membership': 'https://www.niftyindices.com/',
        },
        'source_notes': errors,
        'coverage': {'annual': coverage, 'quarterly': quarterly_coverage},
        'statement_scope': 'Yahoo Finance provider; consolidated/standalone scope NOT independently verified',
    }


def rebuild_exports(companies: list[dict], root: Path = DATA) -> dict:
    companies = [c for c in companies if c.get('company_key') and c.get('symbol')]
    rows = []
    for company in companies:
        doc = load_company(company['company_key'], root)
        if doc:
            rows.append(summary_row(doc))
    rows.sort(key=lambda x: (x['symbol'], x['company_key']))
    _atomic_csv(root / 'company_financial_summary.csv', rows, SUMMARY_FIELDS)
    memberships = _read_csv(ROOT / 'data' / 'india_holdings' / 'constituents.csv')
    by_key = {r['company_key']: r for r in rows}
    groups = {}
    for record in memberships:
        slug = record.get('index_slug', '')
        if not slug:
            continue
        group_id = ('Index', slug)
        if group_id not in groups:
            groups[group_id] = {'group_type': 'Index', 'group_name': record.get('index_name', ''),
                                'index_slug': slug, 'parent_universe': record.get('parent_universe', ''), 'members': []}
        groups[group_id]['members'].append(record)
        if record.get('category') == 'Factor' and record.get('factor_family'):
            family = record['factor_family']
            f_id = ('Factor Family', family)
            if f_id not in groups:
                groups[f_id] = {'group_type': 'Factor Family', 'group_name': family,
                                'index_slug': '', 'parent_universe': 'Multiple', 'members': []}
            groups[f_id]['members'].append(record)
    aggregates = [aggregate_member_financials(v['members'], by_key, v['group_type'],
                  v['group_name'], v['index_slug'], v['parent_universe']) for v in groups.values()]
    aggregates.sort(key=lambda r: (r['group_type'], r['group_name']))
    _atomic_csv(root / 'index_financial_summary.csv', aggregates, AGGREGATE_FIELDS)
    manifest = {
        'built_utc': now_utc(), 'tracked_companies': len(companies),
        'cached_company_snapshots': len(rows),
        'annual_income_coverage': sum(bool(r['income_period']) for r in rows),
        'annual_balance_coverage': sum(bool(r['balance_period']) for r in rows),
        'annual_cashflow_coverage': sum(bool(r['cashflow_period']) for r in rows),
        'price_coverage': sum(r['price'] is not None for r in rows),
        'note': 'Yahoo quotes and statements may be unavailable, stale or of unverified consolidated scope; NSE provides membership, not financials or constituent weights. Screener is linked but not scraped.',
    }
    _atomic_json(root / 'build_summary.json', manifest)
    return manifest


def refresh(companies_csv: Path = COMPANIES_CSV, root: Path = DATA, limit=0, stale_days=14,
            symbols: set[str] | None = None, force=False, delay=1.2, fetcher=fetch_yahoo_company):
    companies = _read_csv(Path(companies_csv))
    if not companies and symbols:
        companies = []  # Direct-ticker research can run without an NSE constituent cache.
    elif not companies:
        raise RuntimeError(f'No NSE companies found in {companies_csv}. Run India NSE Constituents Refresh first; no demo values will be substituted.')
    if symbols:
        # A directly requested .NS ticker may not appear in the 31 NSE index
        # constituent lists. Collect it as a clearly unverified research ticker;
        # NEVER fabricate index membership or merge it into sector/factor cohorts.
        unknown = symbols - {str(c.get('symbol') or '').upper() for c in companies}
        for symbol in sorted(unknown):
            sym = safe_symbol(symbol)
            companies.append({'company_key': 'TICKER:' + sym, 'symbol': sym,
                              'company_name': sym, 'isin': '', 'industry': ''})
            print(f'AD HOC: {sym}.NS (not a verified NSE constituent)', flush=True)
    seen: dict[str, dict] = {}
    for company in companies:
        if company.get('company_key'):
            seen[company['company_key']] = company
    companies = sorted(seen.values(), key=lambda c: (c.get('symbol', ''), c['company_key']))
    rows = _read_csv(root / 'refresh_status.csv')
    by_key = {r['company_key']: r for r in rows if r.get('company_key')}
    refreshed = 0
    errors = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, stale_days))
    for company in companies:
        if symbols and company['symbol'].upper() not in symbols:
            continue
        previous = load_company(company['company_key'], root)
        last_attempt = by_key.get(company['company_key'], {})
        if not force and not symbols and last_attempt.get('status') == 'failed':
            try:
                recent_failure = datetime.fromisoformat(last_attempt['asof_utc'])
                if recent_failure.tzinfo is None:
                    recent_failure = recent_failure.replace(tzinfo=timezone.utc)
                if recent_failure >= datetime.now(timezone.utc) - timedelta(hours=48):
                    continue  # Avoid retrying the same Yahoo 429/errors daily forever.
            except (ValueError, KeyError):
                pass
        if not force and previous:
            try:
                asof = datetime.fromisoformat(previous['retrieved_utc'])
                if asof.tzinfo is None:
                    asof = asof.replace(tzinfo=timezone.utc)
                if asof >= cutoff:
                    continue
            except (KeyError, ValueError):
                pass
        if limit > 0 and refreshed >= limit:
            break
        refreshed += 1
        try:
            doc = fetcher(company)
            if doc.get('company_key') != company['company_key']:
                raise ValueError('Financial record identity does not match NSE company key')
            _atomic_json(company_file(company['company_key'], root), doc)
            by_key[company['company_key']] = {
                'company_key': company['company_key'], 'symbol': company['symbol'],
                'company_name': company['company_name'], 'status': 'ok', 'details': '',
                'asof_utc': now_utc(), 'snapshot_utc': doc.get('retrieved_utc', ''),
            }
            print(f"OK {company['symbol']}: annual periods={len(doc['statements']['annual']['income'])}", flush=True)
        except Exception as exc:
            errors += 1
            by_key[company['company_key']] = {
                'company_key': company['company_key'], 'symbol': company['symbol'],
                'company_name': company['company_name'], 'status': 'failed',
                'details': (f'{type(exc).__name__}: {exc}')[:350], 'asof_utc': now_utc(),
                'snapshot_utc': previous.get('retrieved_utc', '') if previous else '',
            }
            print(f"FAILED {company['symbol']}: {type(exc).__name__}: {str(exc)[:140]}", flush=True)
        if refreshed and refreshed % 20 == 0:
            _atomic_csv(root / 'refresh_status.csv', sorted(by_key.values(), key=lambda x: x['symbol']), STATUS_FIELDS)
            partial = rebuild_exports(companies, root)
            print(f'CHECKPOINT: {refreshed} attempted; {partial["cached_company_snapshots"]} total cached', flush=True)
        if delay > 0:
            time.sleep(delay)
    _atomic_csv(root / 'refresh_status.csv', sorted(by_key.values(), key=lambda x: x['symbol']), STATUS_FIELDS)
    out = rebuild_exports(companies, root)
    out.update({'attempted_this_run': refreshed, 'failed_this_run': errors,
                'successful_this_run': refreshed-errors, 'universe_in_source': len(companies)})
    _atomic_json(root / 'build_summary.json', out)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--limit', type=int, default=0, help='Max attempted, 0 = ALL eligible companies (default: all)')
    p.add_argument('--stale-days', type=int, default=14)
    p.add_argument('--symbols', type=str, default='', help='Comma-separated .NS tickers, even outside the verified NSE index universe')
    p.add_argument('--force', action='store_true')
    p.add_argument('--delay', type=float, default=1.2)
    p.add_argument('--rebuild-only', action='store_true', help='Recompute views from existing cached data')
    p.add_argument('--data-dir', type=Path, default=DATA)
    p.add_argument('--companies-csv', type=Path, default=COMPANIES_CSV)
    args = p.parse_args()
    symbols = set(safe_symbol(x) for x in args.symbols.split(',') if x.strip()) or None
    companies = _read_csv(args.companies_csv)
    if not companies and not symbols:
        raise SystemExit('ERROR: companies.csv empty/missing; run India NSE Constituents Refresh first, or specify --symbols for direct ticker research')
    if args.rebuild_only:
        report = rebuild_exports(companies, args.data_dir)
    else:
        report = refresh(args.companies_csv, args.data_dir, max(0, args.limit),
                         max(0, args.stale_days), symbols, args.force, max(0, args.delay))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
