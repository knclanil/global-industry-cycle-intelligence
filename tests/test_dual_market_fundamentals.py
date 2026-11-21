import sys
import unittest
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from refresh_usa_company_fundamentals import directory_entries
# The USA builder depends on the deployment's UI module; isolate quote logic tests.
import types
if 'usa_research_data' not in sys.modules:
    fake=types.ModuleType('usa_research_data')
    fake.build_memberships=lambda x: x
    fake.STORE=ROOT/'data'/'holdings'
    fake.OUT=ROOT/'data'/'usa_research'/'company_research.csv'
    fake.ROOT=ROOT
    sys.modules['usa_research_data']=fake
from build_usa_research import quote_snapshot

class FundamentalsTests(unittest.TestCase):
    def test_directory_extraction(self):
        raw={'0':{'ticker':'BRK.B','cik_str':1067983,'title':'Berkshire'},
             '1':{'ticker':'MSFT','cik_str':789019,'title':'Microsoft'}}
        rows=directory_entries(raw)
        self.assertEqual([r['ticker'] for r in rows],['BRK-B','MSFT'])
    def test_fresh_quote(self):
        r=quote_snapshot('MSFT',{'MSFT':{'quote_asof':datetime.now(timezone.utc).isoformat(),
                            'currency':'USD','price':100,'pe':22,'pb':5,'market_cap':1e9}})
        self.assertEqual(r['pe'],22)
    def test_stale_quote_excluded(self):
        self.assertEqual(quote_snapshot('MSFT',{'MSFT':{'quote_asof':'2020-01-01','currency':'USD','pe':20}}),{})
    def test_currency_excluded(self):
        self.assertEqual(quote_snapshot('MSFT',{'MSFT':{'quote_asof':datetime.now(timezone.utc).isoformat(),
                                 'currency':'INR','pe':20}}),{})
    def test_nan_excluded(self):
        r=quote_snapshot('MSFT',{'MSFT':{'quote_asof':datetime.now(timezone.utc).isoformat(),
                                  'currency':'USD','pe':float('nan')}})
        self.assertIsNone(r['pe'])

if __name__=='__main__':unittest.main()
