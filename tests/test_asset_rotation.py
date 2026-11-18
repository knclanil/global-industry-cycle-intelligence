import pandas as pd
import global_asset_market_data as g
import usa_asset_market_data as u
import india_asset_market_data as i
from asset_regime import infer_asset_regime

def test_universes_and_benchmarks():
    assert g.BENCHMARK == 'ACWI'
    assert u.BENCHMARK == 'SPY'
    assert i.BENCHMARK == '^NSEI'
    assert all(x.BENCHMARK not in x.SECTORS for x in (g, u, i))

def test_missing_benchmark_is_fatal():
    for module in (g, u, i):
        assert module.validate({}, pd.Timestamp('2026-11-18').date())['status'] == 'FAIL'

def test_regime_is_not_flow_claim():
    rows = pd.DataFrame({'ETF':['VTI','HYG','IEF'], 'Excess vs SPY (pp)':[2,1,-1]})
    assert infer_asset_regime(rows, u.SECTORS)[0] == 'Risk-on'
    assert infer_asset_regime(pd.DataFrame(), u.SECTORS)[0].startswith('Mixed')
