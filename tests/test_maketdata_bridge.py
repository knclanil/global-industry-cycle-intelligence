import unittest
from maketdata_bridge import metrics, score_universe, safe_div
class TestBridge(unittest.TestCase):
 def test_ratio(self):
  self.assertIsNone(safe_div(1,0))
 def test_metrics(self):
  a={'annual':[{'period_end':'2025-12-31','metrics':{'revenue':100,'operating_income':20,'net_income':10,'equity':50,'current_assets':40,'current_liabilities':20,'eps_basic':2}}, {'period_end':'2024-12-31','metrics':{'revenue':80,'eps_basic':1}}]}
  x,n=metrics(a)
  self.assertEqual(n,2);self.assertAlmostEqual(x['Operating margin'],.2);self.assertEqual(x['Current ratio'],2);self.assertEqual(x['EPS growth'],1)
 def test_missing_not_zero(self):
  a={'annual':[{'period_end':'2025-12-31','metrics':{'revenue':100}}]}
  x,n=metrics(a);self.assertIsNone(x['Operating margin'])
 def test_scores_insufficient(self):
  r=score_universe({'A':{'ROE':.1},'B':{'ROE':.2}})
  self.assertIsNone(r['A']['score'])
if __name__=='__main__':unittest.main()
