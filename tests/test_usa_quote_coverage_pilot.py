import sys,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from usa_quote_coverage_pilot import positive,quote_recent,select_targets
class TrialTests(unittest.TestCase):
    def test_missing_not_zero(self):
        self.assertIsNone(positive('nan'))
        self.assertIsNone(positive(0))
    def test_quote_freshness(self):
        self.assertTrue(quote_recent({'price':42,'currency':'USD','quote_asof':datetime.now(timezone.utc).isoformat()}))
        self.assertFalse(quote_recent({'price':42,'currency':'USD','quote_asof':(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()}))
    def test_fundamentals_first_and_skip_fresh(self):
        fin=pd.DataFrame([{'ticker':'MSFT','fundamental_ready':'Yes'}, {'ticker':'AAPL','fundamental_ready':'No'}])
        recent={'MSFT':{'quote_asof':datetime.now(timezone.utc).isoformat(),'price':100,'currency':'USD'}}
        self.assertEqual(select_targets({'MSFT','AAPL','ZZZ'},recent,fin,(),2),['AAPL','ZZZ'])
        self.assertEqual(select_targets({'MSFT','AAPL','ZZZ'},{},fin,(),2),['MSFT','AAPL'])
    def test_reject_unverified(self):
        with self.assertRaises(ValueError):select_targets({'AAPL'},{},pd.DataFrame(),{'NOTINETF'},10)
if __name__=='__main__':unittest.main()
