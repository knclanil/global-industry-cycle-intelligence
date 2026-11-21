"""Shared, read-only India research dataset and membership filter operations.

No API calls are made while rendering the Streamlit application. The opportunity
CSV is authoritative when published. If absent, reconstruct the same universe
from locally cached NSE and finance CSVs, without writing files.
"""
from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
HOLDINGS = ROOT / 'data' / 'india_holdings'
FINANCE = ROOT / 'data' / 'india_financials'
NUMERIC = ('revenue','net_income','roe','operating_margin','revenue_yoy','earnings_yoy',
           'operating_cash_flow','free_cash_flow','debt_to_equity','price','market_cap',
           'pe','pb','ev_to_ebitda','fcf_yield','quality_score','growth_score',
           'valuation_score','research_score','peer_count','factor_count',
           'sector_count','index_count','verified_memberships')


def terms(value):
    if value is None or pd.isna(value):
        return set()
    return {v.strip() for v in str(value).split('|') if v.strip()}


def membership_match(value, selected, match='ANY'):
    if not selected:
        return True
    included = terms(value)
    return set(selected).issubset(included) if match == 'ALL' else bool(included.intersection(selected))


def filter_companies(frame, sectors=(), factors=(), indices=(), match='ANY', query='',
                     fundamentals=False, valuation=False, scored=False):
    """Across categories = AND. Within a multi-select category = ANY or ALL."""
    out = frame.copy()
    for col, selected in [('sectors', sectors), ('factors', factors), ('source_indices', indices)]:
        if selected:
            out = out[out[col].map(lambda v: membership_match(v, selected, match))]
    if query:
        q = query.strip()
        mask = (out['company'].fillna('').str.contains(q, case=False, regex=False) |
                out['ticker'].fillna('').str.contains(q, case=False, regex=False) |
                out['isin'].fillna('').str.contains(q, case=False, regex=False))
        out = out[mask]
    if fundamentals:
        out = out[out['fundamental_ready'] == 'Yes']
    if valuation:
        out = out[out['valuation_ready'] == 'Yes']
    if scored:
        out = out[out['research_score'].notna()]
    return out.copy()


def _csv(path):
    if not path.is_file():
        return []
    import csv
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _load_uncached():
    path = FINANCE / 'opportunity_research.csv'
    if path.is_file():
        data = pd.read_csv(path, dtype=str, keep_default_na=False)
        origin = 'Published opportunity dataset'
    else:
        company_rows = _csv(HOLDINGS / 'companies.csv')
        if not company_rows:
            return pd.DataFrame(), 'Missing data/india_holdings/companies.csv'
        constituent_rows = _csv(HOLDINGS / 'constituents.csv')
        financial_rows = _csv(FINANCE / 'company_financial_summary.csv')
        try:
            from scripts.build_india_opportunity_dataset import build
        except ImportError:
            return pd.DataFrame(), 'Missing scripts/build_india_opportunity_dataset.py; install the end-to-end financial pipeline'
        data = pd.DataFrame(build(company_rows, constituent_rows, financial_rows))
        origin = 'Reconstructed from cached NSE/financial CSVs (not published)'
    if data.empty:
        return data, origin
    for col in ('company_key','company','ticker','isin','industry','sectors','factors',
                'source_indices','fundamental_ready','valuation_ready','research_ready',
                'readiness_reason','coverage_flags','peer_group','income_period',
                'balance_period','cashflow_period','quote_asof','retrieved_utc'):
        if col not in data:
            data[col] = ''
        data[col] = data[col].fillna('').astype(str)
    for col in NUMERIC:
        if col not in data:
            data[col] = pd.NA
        data[col] = pd.to_numeric(data[col], errors='coerce')
    data = data.drop_duplicates(subset=['company_key'], keep='first')
    return data, origin


def load_research():
    import streamlit as st
    watch = [FINANCE/'opportunity_research.csv', FINANCE/'company_financial_summary.csv',
             HOLDINGS/'companies.csv', HOLDINGS/'constituents.csv']
    fingerprint = tuple((str(p),p.stat().st_mtime_ns if p.exists() else 0) for p in watch)
    return _cached_research(fingerprint)


def _cached_research_impl(fingerprint):
    return _load_uncached()

try:
    import streamlit as st
    _cached_research = st.cache_data(show_spinner=False, max_entries=4)(_cached_research_impl)
except ImportError:
    _cached_research = _cached_research_impl


def format_summary(frame):
    show = ['company','ticker','industry','sectors','factors','factor_count','sector_count',
            'roe','revenue_yoy','pe','pb','quality_score','growth_score','valuation_score',
            'research_score','readiness_reason']
    view = frame.copy()
    for field in ('roe','revenue_yoy'):
        view[field] = view[field] * 100
    labels = {'company':'Company','ticker':'Ticker','industry':'Industry',
              'sectors':'Sectors','factors':'Factors','factor_count':'# Factors',
              'sector_count':'# Sectors','roe':'ROE %','revenue_yoy':'Revenue growth %',
              'pe':'P/E','pb':'P/B','quality_score':'Quality score',
              'growth_score':'Growth score','valuation_score':'Valuation score',
              'research_score':'Research score','readiness_reason':'Data coverage / scoring gaps'}
    return view[show].rename(columns=labels)


def report():
    path = FINANCE / 'opportunity_build_report.json'
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    except (ValueError, OSError):
        return {}
