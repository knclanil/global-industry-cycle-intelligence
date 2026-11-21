import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from tempfile import TemporaryDirectory
import json
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import usa_quote_coverage_pilot as quotes
import build_usa_research as research


class QuoteSelection(unittest.TestCase):
    def setUp(self):
        self.members = pd.DataFrame([
            {'company_key':'issuer-aaa','ticker':'AAA'},
            {'company_key':'issuer-bbb','ticker':'BBB'},
            {'company_key':'issuer-ccc','ticker':'CCC'},
            {'company_key':'issuer-invalid','ticker':'2200964D'},
            {'company_key':'issuer-dash','ticker':'-'},
        ])
        # Legacy finance file has no ticker, only company_key.
        self.financial = pd.DataFrame([
            {'company_key':'issuer-bbb','fundamental_ready':'Yes'},
            {'company_key':'issuer-aaa','fundamental_ready':'No'},
            {'company_key':'issuer-ccc','fundamental_ready':'Yes'},
        ])

    def test_legacy_company_key_join_drives_priority(self):
        targets = quotes.select_targets(set(self.members.ticker),{},self.financial,(),2,self.members)
        self.assertEqual(targets,['BBB','CCC'])

    def test_invalid_identifiers_never_queried(self):
        self.assertEqual(quotes.select_targets(set(self.members.ticker),{},self.financial,(),0,self.members),['BBB','CCC','AAA'])
        self.assertFalse(quotes.valid_quote_ticker('-'))
        self.assertFalse(quotes.valid_quote_ticker('2200964D'))
        self.assertTrue(quotes.valid_quote_ticker('BRK.B'))
        with self.assertRaises(ValueError):
            quotes.select_targets(set(self.members.ticker),{},self.financial,{'-'},25,self.members)

    def test_recent_fundamental_skipped(self):
        old={'BBB':{'price':51,'quote_asof':datetime.now(timezone.utc).isoformat(),'currency':'USD'}}
        self.assertEqual(quotes.select_targets(set(self.members.ticker),old,self.financial,(),1,self.members),['CCC'])

    def test_old_file_with_ticker_still_supported(self):
        newer=pd.DataFrame([{'ticker':'CCC','fundamental_ready':'Yes'}])
        self.assertEqual(quotes.select_targets({'AAA','CCC'},{},newer,(),1),['CCC'])


class ResearchCoverage(unittest.TestCase):
    def test_joined_readiness_and_distinct_unscored_status(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            holdings=root/'latest_holdings.parquet'
            holdings.write_bytes(b'exists')
            out=root/'company_research.csv'
            q=root/'quotes.csv'
            now=datetime.now(timezone.utc).isoformat()
            pd.DataFrame([{'ticker':'AAA','price':100,'pe':15,'pb':3,'market_cap':1000,'quote_asof':now,'quote_source':'test','currency':'USD'},
                          {'ticker':'BBB','price':80,'pe':12,'pb':2,'market_cap':800,'quote_asof':now,'quote_source':'test','currency':'USD'}]).to_csv(q,index=False)
            members=pd.DataFrame([{'company_key':'id-a','ticker':'AAA'}, {'company_key':'id-b','ticker':'BBB'}])
            fake_fin={'financial_period':datetime.now(timezone.utc).date().isoformat(),
                      'revenue':100,'net_income':10,'fundamental_ready':'Yes','valuation_ready':'No',
                      'readiness_reason':'placeholder','research_score':None}
            with patch.object(research,'STORE',root), patch.object(research,'ROOT',root.parent), \
                 patch.object(research,'OUT',out), patch.object(research.pd,'read_parquet',return_value=pd.DataFrame()), \
                 patch.object(research,'build_memberships',return_value=members), \
                 patch.object(research,'financials_for',side_effect=lambda t: fake_fin if t=='AAA' else (_ for _ in ()).throw(ValueError('missing'))):
                # research reads ROOT/data/usa_research/quotes.csv; create there.
                real_quote=root.parent/'data'/'usa_research'/'quotes.csv'
                # Avoid writing outside temp root for this test; use patched ROOT as td and STORE as td.
                with patch.object(research,'ROOT',root):
                    quote_path=root/'data'/'usa_research'/'quotes.csv'
                    quote_path.parent.mkdir(parents=True,exist_ok=True)
                    quote_path.write_bytes(q.read_bytes())
                    research.build()
            result=pd.read_csv(out,dtype={'company_key':str})
            self.assertEqual(set(result.ticker),{'AAA','BBB'})
            rowa=result.set_index('ticker').loc['AAA']
            rowb=result.set_index('ticker').loc['BBB']
            self.assertEqual(rowa.research_ready,'Yes')
            self.assertTrue(pd.isna(rowa.research_score))
            self.assertEqual(rowb.research_ready,'No')
            report=json.loads((root/'build_report.json').read_text())
            self.assertEqual(report['research_ready'],1)
            self.assertEqual(report['quote_without_fundamentals'],1)
            self.assertEqual(report['fully_scored'],0)

if __name__=='__main__':unittest.main()
