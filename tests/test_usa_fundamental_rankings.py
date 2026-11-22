import importlib.util
import unittest
from datetime import date
from pathlib import Path
import pandas as pd

mod_path=Path(__file__).resolve().parents[1]/'scripts/build_usa_fundamental_rankings.py'
spec=importlib.util.spec_from_file_location('usa_rank',mod_path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestRank(unittest.TestCase):
 def test_only_tie_uses_cap(self):
  df=pd.DataFrame([
   dict(ticker='A',roe=20,current_ratio=2,operating_margin=20,net_margin=15,eps_growth_pct=10,market_cap=100),
   dict(ticker='B',roe=30,current_ratio=1,operating_margin=15,net_margin=10,eps_growth_pct=5,market_cap=10000),
   dict(ticker='C',roe=20,current_ratio=2,operating_margin=20,net_margin=15,eps_growth_pct=10,market_cap=200),
  ])
  out=m.rank_frame(df).set_index('ticker')
  self.assertEqual(int(out.loc['C','final_rank']),1)
  self.assertEqual(int(out.loc['A','final_rank']),2)
  self.assertEqual(int(out.loc['B','final_rank']),3)
  self.assertEqual(int(out.loc['A','total_fundamental_rank']),int(out.loc['C','total_fundamental_rank']))
 def test_missing_never_ranked(self):
  df=pd.DataFrame([dict(ticker='X',roe=10,current_ratio=None,operating_margin=10,net_margin=10,eps_growth_pct=10,market_cap=4)])
  out=m.rank_frame(df)
  self.assertFalse(bool(out.iloc[0]['ranking_eligible']))
  self.assertTrue(pd.isna(out.iloc[0]['final_rank']))
 def test_eps_growth_positive_base(self):
  def fact(t,fy,start,end,amount,unit='USD'):
   return {'val':amount,'start':start,'end':end,'form':'10-K','fp':'FY','fy':fy,'filed':f'{fy+1}-02-01','accn':'X'}
  facts={'facts':{'us-gaap':{}}}
  for name,amount in [('RevenueFromContractWithCustomerExcludingAssessedTax',100),('NetIncomeLoss',10),('OperatingIncomeLoss',20),('AssetsCurrent',40),('LiabilitiesCurrent',20),('StockholdersEquity',50)]:
   instant=name in ('AssetsCurrent','LiabilitiesCurrent','StockholdersEquity')
   ob=fact(name,2024,'2024-01-01','2024-12-31',amount)
   if instant:ob.pop('start')
   facts['facts']['us-gaap'][name]={'units':{'USD':[ob]}}
  facts['facts']['us-gaap']['EarningsPerShareDiluted']={'units':{'USD/shares':[fact('',2024,'2024-01-01','2024-12-31',2),fact('',2023,'2023-01-01','2023-12-31',1)]}}
  values,_=m.annual_fields(facts,date(2025,6,1))
  self.assertEqual(values['roe'],20)
  self.assertEqual(values['current_ratio'],2)
  self.assertEqual(values['operating_margin'],20)
  self.assertEqual(values['net_margin'],10)
  self.assertEqual(values['eps_growth_pct'],100)
 def test_reference_links(self):
  urls=m.reference_links('AAPL')
  self.assertEqual(len(urls),10)
  self.assertIn('/stocks/AAPL/financials/ratios/',urls['stockanalysis_ratios_url'])
 def test_exact_ties_share_final_rank(self):
  rows=[dict(ticker=x,roe=1,current_ratio=1,operating_margin=1,net_margin=1,eps_growth_pct=1,market_cap=100) for x in ('A','B')]
  out=m.rank_frame(pd.DataFrame(rows))
  self.assertEqual(list(out.final_rank),[1,1])

if __name__=='__main__':unittest.main()
