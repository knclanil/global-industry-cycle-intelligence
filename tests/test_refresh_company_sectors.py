from pathlib import Path
import sys
import tempfile
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh_company_sectors import collect_universe, fetch_one, refresh

class FakeYF:
    calls = []
    class Ticker:
        def __init__(self, ticker):
            FakeYF.calls.append(ticker)
            self.info = {'NVDA': {'sector': 'Technology', 'quoteType':'EQUITY'},
                         'SPY': {'quoteType':'ETF'}}.get(ticker, {})

def test_fetch_one():
    assert fetch_one('NVDA', FakeYF, sleep=lambda _:None)['Sector'] == 'Technology'
    assert fetch_one('SPY', FakeYF, sleep=lambda _:None)['Status'] == 'non_company'
    assert fetch_one('MISSING', FakeYF, sleep=lambda _:None)['Status'] == 'unmapped'

def test_universe_and_refresh():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = root/'data'/'india_holdings'
        p.mkdir(parents=True)
        pd.DataFrame({'symbol':['NVDA', 'SPY', 'NVDA']}).to_csv(p/'constituents.csv',index=False)
        universe = collect_universe(root)
        assert set(universe.Ticker) == {'NVDA.NS', 'SPY.NS'}
        summary = refresh(root, yf_module=FakeYF, delay=0, sleep=lambda _: None)
        assert summary['total_tickers'] == 2
        assert (root/'data/dashboard_cache/company_sectors/company_sector_mapping.csv').exists()
