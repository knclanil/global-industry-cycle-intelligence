import pandas as pd
import sys
import types
try:
    import streamlit
except ImportError:
    fake = types.ModuleType('streamlit')
    def cached(*args, **kwargs):
        def wrap(func): return func
        return wrap
    fake.cache_data = cached
    sys.modules['streamlit'] = fake
from regional_workspace import filter_companies, company_intersections


def sample():
    return pd.DataFrame([
        {"company_key":"1", "symbol":"AAA", "country":"India", "sector_indices":"Technology | Manufacturing", "factor_families":"Growth | Quality"},
        {"company_key":"2", "symbol":"BBB", "country":"India", "sector_indices":"Technology", "factor_families":"Growth"},
        {"company_key":"3", "symbol":"CCC", "country":"USA", "sector_indices":"Energy", "factor_families":"Value"},
    ])


def test_filtered_companies():
    d=sample()
    assert len(filter_companies(d,countries=["India"],sectors=["Technology"],factors=["Growth"])) == 2
    assert len(filter_companies(d,sectors=["Technology","Manufacturing"],mode="ALL")) == 1
    assert len(filter_companies(d,sectors=["Technology"],factors=["Value"])) == 0


def test_overlap_counts():
    m=company_intersections(sample())
    row=m.loc[m.sector_index.eq("Technology") & m.factor_family.eq("Growth")]
    assert int(row.companies.iloc[0]) == 2
    assert len(m) == 5
