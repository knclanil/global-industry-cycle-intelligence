import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_india_opportunity_dataset as engine
import install_india_opportunity_ui as installer

class EndToEndOfflineTests(unittest.TestCase):
    def setUp(self):
        self.companies=[{'company_key':f'ISIN:{i}', 'company_name':f'Company {i}',
                         'symbol':f'TK{i}', 'isin':f'ISIN{i}','industry':'Information Technology'} for i in range(9)]
        self.members=[{'company_key':f'ISIN:{i}', 'source_type':'direct_nse',
                       'category':'Factor','factor_family':'Quality','index_slug':'quality_a','index_name':'Nifty Quality'} for i in range(9)]
        self.members += [{'company_key':'ISIN:0', 'source_type':'direct_nse',
                          'category':'Factor','factor_family':'Value','index_slug':'value_b','index_name':'Nifty Value'},
                         {'company_key':'ISIN:0', 'source_type':'direct_nse',
                          'category':'Factor','factor_family':'Quality','index_slug':'quality_a','index_name':'Nifty Quality'},
                         {'company_key':'ISIN:0', 'source_type':'direct_nse',
                          'category':'Sector','index_slug':'nifty_it','index_name':'Nifty IT'}]
        self.fin=[]
        for i in range(9):
            self.fin.append({'company_key':f'ISIN:{i}','revenue':str(100+i),
                             'net_income':str(9+i),'roe':str(.1+i*.01),
                             'operating_margin':str(.2+i*.01),'revenue_yoy':str(.12+i*.01),
                             'earnings_yoy':str(.11+i*.01),'debt_to_equity':'0.5',
                             'fcf_yield':str(.025+i*.001), 'pe':str(20+i), 'pb':str(3+i*.1),
                             'price':'100','financial_period':'2026-03-31',
                             'income_period':'2026-03-31','quote_asof':'2026-11-20'})
    def test_one_row_per_company_and_distinct_factor_memberships(self):
        rows=engine.build(self.companies,self.members,self.fin,today=date(2026,11,21))
        self.assertEqual(len(rows),9)
        first=next(r for r in rows if r['ticker']=='TK0')
        self.assertEqual(first['factor_count'],2)
        self.assertEqual(first['sector_count'],1)
        self.assertEqual(first['verified_memberships'],3)
        self.assertEqual(first['factors'],'Quality | Value')
    def test_partial_coverage_never_gets_fabricated_score(self):
        self.fin[0]['pe']='';self.fin[0]['pb']=''
        rows=engine.build(self.companies,self.members,self.fin,today=date(2026,11,21))
        r=next(r for r in rows if r['ticker']=='TK0')
        self.assertEqual(r['valuation_ready'],'No')
        self.assertIsNone(r['research_score'])
    def test_stale_quote_not_scored(self):
        self.fin[0]['quote_asof']='2025-01-01'
        r=next(r for r in engine.build(self.companies,self.members,self.fin,today=date(2026,11,21)) if r['ticker']=='TK0')
        self.assertEqual(r['quote_fresh'],'No')
        self.assertIsNone(r['research_score'])
    def test_missing_peer_group_does_not_create_fake_scores(self):
        rows=engine.build(self.companies[:2],self.members[:2],self.fin[:2],today=date(2026,11,21))
        self.assertTrue(all(r['research_score'] is None for r in rows))
    def test_independent_graph_not_edited(self):
        source="def render_india_sector_factor_financials():\n    tabs = st.tabs(['Sector & thematic', 'Factor families', 'All source indices', 'Sector × factor matrix', 'Coverage & diagnostics'])\n"
        modified=installer.patch(source)
        self.assertIn("'Investment Opportunities'",modified)
        self.assertEqual(modified,installer.patch(modified))
        with self.assertRaises(RuntimeError):installer.patch('unknown source')

if __name__=='__main__':unittest.main()
