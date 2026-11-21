import unittest
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
# Mock the existing repository labeler for isolated unit tests; deployment uses real code.
import types
stub=types.ModuleType('holdings_intelligence')
def display_strategy(title,group):
    title=title.lower()
    for name in ('quality','value','growth','technology'):
        if name in title:return name.title()
    return 'Other / Unclassified'
stub.display_strategy=display_strategy
sys.modules.setdefault('holdings_intelligence',stub)
from usa_research_data import build_memberships,filter_companies
from scripts.install_usa_research_pages import patch

class USAResearchTests(unittest.TestCase):
    def setUp(self):
        self.h=pd.DataFrame([
            dict(issuer_id='TICKER_COUNTRY:AAA|US',ticker='AAA',company='Alpha',country='United States',
                 category='factor',portfolio_id='1',fund_title='iShares Quality Factor',weight=2,as_of='2026-11-01'),
            dict(issuer_id='TICKER_COUNTRY:AAA|US',ticker='AAA',company='Alpha',country='United States',
                 category='factor',portfolio_id='2',fund_title='iShares Value Factor',weight=3,as_of='2026-11-01'),
            dict(issuer_id='TICKER_COUNTRY:AAA|US',ticker='AAA',company='Alpha',country='United States',
                 category='sector',portfolio_id='3',fund_title='iShares Technology ETF',weight=4,as_of='2026-11-01'),
            dict(issuer_id='TICKER_COUNTRY:AAA|GB',ticker='AAA-GB',company='Alpha GB',country='United Kingdom',
                 category='factor',portfolio_id='1',fund_title='iShares Quality Factor',weight=1,as_of='2026-11-01'),
            dict(issuer_id='TICKER_COUNTRY:BBB|US',ticker='BBB',company='Beta',country='United States',
                 category='global_factor',portfolio_id='4',fund_title='iShares World Quality Factor',weight=1,as_of='2026-11-01')])
    def test_unique_us_issuer(self):
        x=build_memberships(self.h)
        self.assertEqual(len(x),1)
        self.assertEqual(x.iloc[0]['factor_count'],2)
        self.assertEqual(x.iloc[0]['membership_count'],3)
    def test_any_all(self):
        x=build_memberships(self.h)
        self.assertEqual(len(filter_companies(x,factors=['Quality','Value'],mode='ALL')),1)
        self.assertEqual(len(filter_companies(x,factors=['Quality','Growth'],mode='ALL')),0)
        self.assertEqual(len(filter_companies(x,factors=['Quality','Growth'],mode='ANY')),1)
    def test_nav_install_idempotent(self):
        app=Path(__file__).resolve().parents[2]/'new_india_workspace'/'app.py'
        if not app.exists():return
        original=app.read_text()
        self.assertEqual(patch(patch(original)),patch(original))

if __name__=='__main__':unittest.main()
