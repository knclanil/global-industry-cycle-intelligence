"""Read-only materialization rules and source identity safeguards."""
import importlib.util
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_dashboard_cache',ROOT/'scripts/build_dashboard_cache.py')
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def test_india_unique_and_memberships():
    company,indices,matrix=b.build_india()
    if not company.empty:
        assert company.company_key.is_unique
        assert len(indices) == 31
        assert int(company.index_memberships.sum()) == 975
        assert len(company) == 328
        assert (matrix.companies >= 1).all()


def test_missing_financial_values_not_zero():
    company,idx,_=b.build_india()
    assert not company.empty
    if 'revenue' in company:
        assert pd.to_numeric(company.revenue,errors='coerce').notna().sum() == 0
        assert company.financial_status.eq('Available').sum() == 0
    result=b.index_financials('India',company,idx)
    assert result.financial_records.sum() == 0
    assert result.median_revenue.isna().all()


def test_atomic_manifest_build():
    result=b.build()
    assert result['regions']['India']['companies'] == 328
    assert (b.OUTPUT/'manifest.json').exists()
