#!/usr/bin/env python3
"""Incremental, conservative India fundamentals collection + metric-level audit.

Reuses the repository's existing verified NSE universe, Yahoo fetcher, JSON
snapshots and financial KPIs. Does NOT invent missing metrics or scrape Screener.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import india_financial_data as data
import refresh_india_financials as original

METRICS = ('revenue','net_income','operating_margin','roe','roa','revenue_yoy',
           'earnings_yoy','operating_cash_flow','free_cash_flow','total_debt',
           'debt_to_equity','market_cap','price','pe','pb','ev_to_ebitda','fcf_yield')
AUDIT_FIELDS = ('company_key','symbol','company_name','snapshot','income','balance',
                'cashflow','quote','fundamental_ready','valuation_ready',
                'income_period','balance_period','cashflow_period','retrieved_utc',
                'missing_metrics') + METRICS

# Compatibility for upstream yfinance releases: canonicalized row label matching.
# Only labels already explicitly recognized by the application's ALIAS dictionary
# are accepted; we do not infer a different metric or manufacture values.
def install_normalization_compatibility():
    old = data.normalize_sheet
    def compatible(sheet, metric_keys):
        if sheet is None or not hasattr(sheet, 'index') or sheet.empty:
            return old(sheet, metric_keys)
        frame = sheet.copy()
        def canonical(label):
            return ''.join(c.lower() for c in str(label) if c.isalnum())
        known = {canonical(alias): alias for keys in data.ALIAS.values() for alias in keys}
        frame.index = [known.get(canonical(label), str(label).strip()) for label in frame.index]
        return old(frame, metric_keys)
    data.normalize_sheet = compatible


def valid(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def audit(companies_csv=original.COMPANIES_CSV, output=data.DATA, write=True):
    companies = original._read_csv(Path(companies_csv))
    if not companies:
        raise RuntimeError('Verified NSE companies.csv is missing/empty')
    status = {r['company_key']:r for r in original._read_csv(Path(output)/'refresh_status.csv') if r.get('company_key')}
    rows = []
    for c in companies:
        key = c.get('company_key')
        if not key: continue
        doc = data.load_company(key, Path(output))
        summary = data.summary_row(doc) if doc else {}
        income = bool(summary.get('income_period'))
        balance = bool(summary.get('balance_period'))
        cashflow = bool(summary.get('cashflow_period'))
        # These are minimum gates, not proof of investment quality.
        fundamental = all(valid(summary.get(k)) for k in ('revenue','net_income','roe'))
        valuation = fundamental and valid(summary.get('price')) and (valid(summary.get('pe')) or valid(summary.get('pb')))
        row = dict(company_key=key, symbol=c.get('symbol',''), company_name=c.get('company_name',''),
                   snapshot=bool(doc), income=income, balance=balance, cashflow=cashflow,
                   quote=valid(summary.get('price')), fundamental_ready=fundamental,
                   valuation_ready=valuation, income_period=summary.get('income_period',''),
                   balance_period=summary.get('balance_period',''),
                   cashflow_period=summary.get('cashflow_period',''),
                   retrieved_utc=summary.get('retrieved_utc',''),
                   missing_metrics=' | '.join(k for k in METRICS if not valid(summary.get(k))))
        row.update({k:summary.get(k) for k in METRICS})
        rows.append(row)
    counts = {k: sum(bool(r[k]) for r in rows) for k in
              ('snapshot','income','balance','cashflow','quote','fundamental_ready','valuation_ready')}
    metric_counts = {k:sum(valid(r[k]) for r in rows) for k in METRICS}
    failures = Counter(r.get('status','unknown') for r in status.values())
    report = {'built_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
              'universe':len(rows),'coverage':counts,'metric_coverage':metric_counts,
              'collection_status_counts':dict(failures),
              'quality_policy':'Missing is unknown (never zero). Fundamental readiness requires revenue, net_income, roe; valuation also requires price and PE or PB. No rankings until coverage adequate.',
              'source':'NSE verified constituents + cached Yahoo Finance snapshots; no Screener scraping'}
    if write:
        Path(output).mkdir(parents=True, exist_ok=True)
        original._atomic_csv(Path(output)/'kpi_coverage_by_company.csv',rows,list(AUDIT_FIELDS))
        original._atomic_json(Path(output)/'kpi_coverage_report.json',report)
    return report


def fetch_with_diagnostics(company):
    # One attempt: the existing refresh() applies a 48h cooldown to failures,
    # preventing aggressive retries against a rate-limited provider.
    try:
        return original.fetch_yahoo_company(company)
    except Exception as ex:
        raise RuntimeError(f'Yahoo financial statement fetch: {type(ex).__name__}: {str(ex)[:230]}') from ex


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--limit',type=int,default=25,help='Max requests per run; 0=entire eligible NSE universe')
    p.add_argument('--delay',type=float,default=2.0)
    p.add_argument('--stale-days',type=int,default=30)
    p.add_argument('--symbols',default='',help='Comma-separated NSE symbols for manual diagnostics')
    p.add_argument('--force',action='store_true')
    p.add_argument('--audit-only',action='store_true')
    args=p.parse_args()
    install_normalization_compatibility()
    if not args.audit_only:
        selected={data.safe_symbol(s) for s in args.symbols.split(',') if s.strip()} or None
        result=original.refresh(limit=max(0,args.limit),stale_days=max(0,args.stale_days),
                                symbols=selected,force=args.force,delay=max(0,args.delay),
                                fetcher=fetch_with_diagnostics)
        print('COLLECTION:',json.dumps(result,indent=2),flush=True)
    report=audit()
    print('KPI COVERAGE:',json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    main()
