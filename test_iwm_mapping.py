import sys
import types
import pandas as pd
import pytest

sys.modules.setdefault('holdings_intelligence', types.SimpleNamespace(
    SECTORS=[], GLOBAL_SECTORS=['239751'], FACTORS=['239710'], GLOBAL_FACTORS=[]
))
from leading_lagging_engine import source_signal_mapping


def test_iwm_portfolio_maps_to_small_cap_if_valid():
    holdings = pd.DataFrame([{'portfolio_id':'239710','fund_title':'iShares Russell 2000 ETF'}])
    signals = pd.DataFrame([dict(source_id='IWM',kind='factor',label='Small Cap',quadrant='Weakening')])
    mapping, missing = source_signal_mapping('USA', holdings, signals)
    assert not missing
    assert mapping['239710']['source_id']=='IWM'
    assert mapping['239710']['quadrant']=='Weakening'
    assert mapping['239710']['mapping_method']=='explicit_category_proxy'


def test_iwm_requires_valid_price_signal():
    holdings = pd.DataFrame([{'portfolio_id':'239710','fund_title':'iShares Russell 2000 ETF'}])
    signals = pd.DataFrame([dict(source_id='USMV',kind='factor',label='Minimum Volatility',quadrant='Leading')])
    mapping, missing = source_signal_mapping('USA', holdings, signals)
    assert not mapping
    assert 'IWM' in missing[0]['Reason']


def test_iwm_is_factor_not_sector():
    holdings = pd.DataFrame([{'portfolio_id':'239710','fund_title':'iShares Russell 2000 ETF'}])
    signals = pd.DataFrame([dict(source_id='IWM',kind='sector',label='Small Cap',quadrant='Leading')])
    mapping, missing = source_signal_mapping('USA', holdings, signals)
    assert not mapping
