import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from usa_sec_cache_reader import ticker_directory,cached_companyfacts
from usa_financial_gap_report import generate
from usa_quote_coverage_pilot import valid_quote_ticker, select_targets

class USAAutopilotTests(unittest.TestCase):
    def test_cached_official_ticker_cik_only(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            folder=root/'data/fundamentals';folder.mkdir(parents=True)
            (folder/'sec_company_directory.json').write_text(json.dumps([{'ticker':'BRK-B','cik_str':1067983},{'ticker':'AAPL','cik_str':320193}]))
            (folder/'facts_0000320193.json').write_text(json.dumps({'cik':320193,'facts':{'us-gaap':{}}}))
            directory=ticker_directory(root)
            self.assertEqual(directory['AAPL'],320193)
            self.assertEqual(cached_companyfacts(root,'AAPL',directory)[1],320193)
            self.assertRaises(ValueError,cached_companyfacts,root,'MSFT',directory)
    def test_readiness_overlap_and_no_fake_scores(self):
        df=pd.DataFrame([{'company_key':'a','ticker':'AAPL','revenue':123,'price':70,'pe':15,'fundamental_ready':'Yes','valuation_ready':'Yes','research_ready':'Yes'},
                         {'company_key':'b','ticker':'MSFT','revenue':123,'fundamental_ready':'Yes','valuation_ready':'No','research_ready':'No'}])
        report,gaps=generate(df)
        self.assertEqual(report['both_ready'],1)
        self.assertEqual(report['research_score_populated'],0)
        self.assertEqual(len(gaps),2)
    def test_quote_targets_skip_invalid_and_prioritize_fundamentals(self):
        f=pd.DataFrame([{'ticker':'MSFT','fundamental_ready':'Yes'}])
        got=select_targets({'-','2200964D','AAPL','MSFT'},{},f,limit=5)
        self.assertEqual(got,['MSFT','AAPL'])
        self.assertFalse(valid_quote_ticker('2200964D'))
if __name__=='__main__':unittest.main()
