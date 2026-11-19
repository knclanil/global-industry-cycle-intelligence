"""Fixtures contain synthetic numbers strictly for unit tests, not app datasets."""
import csv
import math
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india_financial_data import (
    normalize_yahoo_statements, build_kpis, equity_dcf_proxy, liquidation_proxy,
    aggregate_member_financials, company_file, screener_url, yahoo_symbol,
)
from scripts.refresh_india_financials import refresh, rebuild_exports


def make_document(company_key='ISIN:INTESTCOMP1', symbol='TEST'):
    ai = pd.DataFrame({
        pd.Timestamp('2026-03-31'): [1_200_000_000, 240_000_000, 600_000_000, 12, -10_000_000],
        pd.Timestamp('2025-03-31'): [1_000_000_000, 180_000_000, 520_000_000, 9, -8_000_000],
    }, index=['Total Revenue','Net Income','Operating Income','Diluted EPS','Interest Expense'])
    ab = pd.DataFrame({pd.Timestamp('2026-03-31'): [3_000_000_000, 1_200_000_000, 1_800_000_000, 500_000_000, 400_000_000, 1_800_000_000, 600_000_000, 100_000_000]},
                      index=['Total Assets','Total Liabilities Net Minority Interest','Stockholders Equity',
                             'Cash And Cash Equivalents','Total Debt','Current Assets',
                             'Current Liabilities','Ordinary Shares Number'])
    ac = pd.DataFrame({pd.Timestamp('2026-03-31'): [450_000_000, -100_000_000]},
                      index=['Operating Cash Flow','Capital Expenditure'])
    qi = pd.DataFrame({pd.Timestamp('2026-06-30'): [350_000_000, 60_000_000, 3]},
                      index=['Total Revenue','Net Income','Diluted EPS'])
    qb = pd.DataFrame({pd.Timestamp('2026-06-30'): [3_400_000_000]}, index=['Total Assets'])
    statements = normalize_yahoo_statements(ai, ab, ac, qi, qb, None)
    return {'company_key':company_key,'symbol':symbol,'company_name':'Test Company',
            'isin':'INTESTCOMP1','industry':'Test Industry','sector':'Industrials',
            'yahoo_ticker':symbol+'.NS','currency':'INR',
            'quote':{'price':20,'market_cap':2_000_000_000,'shares_outstanding':100_000_000,
                     'currency':'INR','asof_utc':'2026-11-19T14:00:00+00:00'},
            'retrieved_utc':'2026-11-19T14:00:00+00:00','statements':statements}


def test_financial_normalization_and_latest_values():
    doc = make_document()
    metrics = build_kpis(doc)['metrics']
    assert metrics['revenue'] == 1_200_000_000
    assert metrics['capital_expenditure'] == 100_000_000
    assert metrics['free_cash_flow'] == 350_000_000
    assert metrics['net_debt'] == -100_000_000
    assert math.isclose(metrics['revenue_yoy'], 0.2)
    assert math.isclose(metrics['operating_margin'], 0.5)
    assert math.isclose(metrics['book_value_per_share'], 18)
    assert math.isclose(metrics['graham_number'], math.sqrt(22.5*12*18))
    assert metrics['price'] == 20
    assert math.isclose(metrics['pe'], 20/12)


def test_quarterly_values_are_not_annualized_for_valuation():
    doc = make_document()
    q = build_kpis(doc, 'quarterly')['metrics']
    assert q['revenue'] == 350_000_000
    assert q.get('graham_number') is None
    assert q.get('pe') is None
    assert q.get('fcf_yield') is None


def test_missing_financial_inputs_not_zero():
    doc = make_document()
    metrics = build_kpis(doc)['metrics']
    assert metrics.get('tangible_book_per_share') is None  # goodwill missing
    assert metrics.get('ncav_per_share') is None  # preferred claims missing
    assert metrics.get('fcf_yoy') is None  # prior cashflow year missing
    assert liquidation_proxy(100, 20, 40, 2, preferred_claim=None) is None
    assert liquidation_proxy(100, 20, 40, 2, preferred_claim=0) is not None
    assert equity_dcf_proxy(-1, 10) is None
    assert equity_dcf_proxy(100, 10, discount_pct=3, terminal_pct=5) is None


def test_sector_factor_unique_member_medians():
    members = [{'company_key': 'a'}, {'company_key': 'a'}, {'company_key': 'b'}, {'company_key': 'c'}]
    cached = {'a': {'revenue_yoy': 0.1, 'income_period':'2026-03-31'},
              'b': {'revenue_yoy': 0.3, 'income_period':'2026-03-31'}}
    agg = aggregate_member_financials(members, cached, 'Factor Family', 'Value')
    assert agg['constituents'] == 3
    assert agg['companies_with_snapshots'] == 2
    assert math.isclose(agg['median_revenue_yoy'], 0.2)
    assert agg['n_revenue_yoy'] == 2
    assert math.isclose(agg['pct_with_income'], 0.0)  # revenue not provided in fixture


def test_source_uris_and_company_identity(tmp_path):
    assert yahoo_symbol('RELIANCE') == 'RELIANCE.NS'
    assert screener_url('RELIANCE') == 'https://www.screener.in/company/RELIANCE/consolidated/'
    assert company_file('ISIN:ONE', tmp_path) != company_file('ISIN:TWO', tmp_path)


def test_mock_batch_persistence_and_second_run_skip(tmp_path):
    root = tmp_path / 'financials'
    directory = tmp_path / 'holdings'
    directory.mkdir()
    companies = directory / 'companies.csv'
    with companies.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['company_key','symbol','company_name','isin','industry'])
        w.writeheader()
        w.writerows([{'company_key':'ISIN:INTESTCOMP1','symbol':'TEST', 'company_name':'Test Company',
                      'isin':'INTESTCOMP1','industry':'Industrials'}])
    runs = []
    def mock_fetch(company):
        runs.append(company['symbol'])
        return make_document(company['company_key'], company['symbol'])
    out = refresh(companies, root, limit=5, delay=0, fetcher=mock_fetch)
    assert out['cached_company_snapshots'] == 1
    assert out['successful_this_run'] == 1
    assert len(runs) == 1
    out2 = refresh(companies, root, limit=5, delay=0, fetcher=mock_fetch)
    assert out2['attempted_this_run'] == 0
    assert len(runs) == 1
    assert (root / 'company_financial_summary.csv').is_file()
    assert (root / 'index_financial_summary.csv').is_file()


def test_full_universe_refresh_has_no_25_company_cap(tmp_path):
    """The full refresh attempts all eligible records and saves their KPI summaries."""
    root = tmp_path / 'financials'
    directory = tmp_path / 'holdings'
    directory.mkdir()
    companies = directory / 'companies.csv'
    with companies.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['company_key', 'symbol', 'company_name', 'isin', 'industry'])
        writer.writeheader()
        for i in range(27):
            writer.writerow({'company_key': f'ISIN:INTEST{i:05}', 'symbol': f'TEST{i}',
                             'company_name': f'Company {i}', 'isin': f'INTEST{i:05}', 'industry': 'Test'})
    fetched = []
    def stub(row):
        fetched.append(row['symbol'])
        return make_document(row['company_key'], row['symbol'])
    stats = refresh(companies, root, limit=0, delay=0, fetcher=stub)
    assert stats['attempted_this_run'] == 27
    assert stats['cached_company_snapshots'] == 27
    assert len(fetched) == 27
    assert (root / 'refresh_status.csv').exists()


def test_direct_ticker_research_is_not_disguised_as_nse_membership(tmp_path):
    root = tmp_path / 'financials'
    not_existing = tmp_path / 'no_companies.csv'
    def stub(row):
        assert row['company_key'] == 'TICKER:MGL'
        assert row['symbol'] == 'MGL'
        assert row.get('isin', '') == ''
        return make_document(row['company_key'], row['symbol'])
    stats = refresh(not_existing, root, limit=0, symbols={'MGL'}, delay=0, fetcher=stub)
    assert stats['cached_company_snapshots'] == 1
    assert stats['successful_this_run'] == 1
    saved = __import__('india_financial_data').load_company('TICKER:MGL', root)
    assert saved['symbol'] == 'MGL'
    assert saved['company_key'].startswith('TICKER:')
