import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from usa_sec_cache_reader import normalize_ticker
from usa_quote_coverage_pilot import valid_quote_ticker
from build_usa_fundamental_rankings import rank_frame, FIELDS

class RecoveryFollowup(unittest.TestCase):
    def test_share_classes(self):
        self.assertEqual(normalize_ticker('BRK B'),'BRK-B')
        self.assertEqual(normalize_ticker('BF.A'),'BF-A')
        self.assertTrue(valid_quote_ticker('BRK B'))
        self.assertFalse(valid_quote_ticker('2200964D'))
    def test_missing_reasons(self):
        rows=[dict(ticker='ABC',market_cap=None,roe=3,current_ratio=None,operating_margin=2,net_margin=1,eps_growth_pct=4)]
        result=rank_frame(pd.DataFrame(rows))
        self.assertIn('current_ratio',result.iloc[0]['ranking_reason'])
        self.assertTrue(pd.isna(result.iloc[0]['final_rank']))
    def test_financial_ineligible_even_if_incomplete(self):
        row=dict(ticker='BANK',market_cap=None,industry='Commercial Banks',sectors='Financials')
        row.update({f:None for f in FIELDS})
        result=rank_frame(pd.DataFrame([row]))
        self.assertIn('Financial institution',result.iloc[0]['ranking_reason'])
if __name__=='__main__': unittest.main()
