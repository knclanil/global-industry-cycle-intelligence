import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_usa_fundamental_rankings import _annual_observation,annual_fields

def fact(value,year,tag,frame=True,fy=None):
    o={'form':'10-K','fp':'FY','fy':fy or year,'filed':f'{year+1}-02-10','start':f'{year}-01-01','end':f'{year}-12-31','val':value,'accn':'test'}
    if frame:o['frame']=f'CY{year}'
    return o

class RecoveryTests(unittest.TestCase):
    def test_comparative_fy_mismatch(self):
        f={'facts':{'us-gaap':{'EarningsPerShareDiluted':{'units':{'USD/shares':[fact(2,2024,'EPS',fy=2025)]}}}}}
        self.assertEqual(_annual_observation(f,'eps_diluted',2024,date(2026,1,1))['value'],2)
    def test_negative_to_positive_eps(self):
        facts={'facts':{'us-gaap':{
            'EarningsPerShareDiluted':{'units':{'USD/shares':[fact(-2,2024,'EPS'),fact(1,2025,'EPS')]}},
            'Revenues':{'units':{'USD':[fact(100,2025,'rev')]}},
            'NetIncomeLoss':{'units':{'USD':[fact(10,2025,'net')]}},
            'StockholdersEquity':{'units':{'USD':[{'form':'10-K','fp':'FY','fy':2025,'filed':'2026-02-10','end':'2025-12-31','val':50}]}}}}}
        values,_=annual_fields(facts,date(2026,6,1))
        self.assertEqual(values['eps_growth_pct'],150)
    def test_zero_prior_eps_undefined(self):
        facts={'facts':{'us-gaap':{'EarningsPerShareDiluted':{'units':{'USD/shares':[fact(0,2024,'EPS'),fact(1,2025,'EPS')]}}}}}
        self.assertEqual(_annual_observation(facts,'eps_diluted',2024,date(2026,6,1))['value'],0)
if __name__=='__main__':unittest.main()
