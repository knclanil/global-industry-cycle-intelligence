import unittest
from datetime import date
from scripts.build_usa_fundamental_rankings import annual_fields

def obs(v, year, instant=False):
    d={"val":v,"end":f"{year}-12-31","filed":f"{year+1}-02-20","form":"10-K","fp":"FY","fy":year+1}
    if not instant:d["start"]=f"{year}-01-01"
    return d

def facts(fields):
    return {"facts":{"us-gaap":{k:{"units":{"USD":[obs(v,2025, k in ('StockholdersEquity','AssetsCurrent','LiabilitiesCurrent','Liabilities','LiabilitiesNoncurrent'))]}} for k,v in fields.items()}}}

class Recovery(unittest.TestCase):
    def test_operating_income_derived_from_same_period(self):
        f=facts({'Revenues':100,'NetIncomeLoss':10,'StockholdersEquity':50,'GrossProfit':45,'OperatingExpenses':25,'AssetsCurrent':80,'LiabilitiesCurrent':40})
        metrics, ev=annual_fields(f,date(2026,11,23))
        self.assertEqual(metrics['operating_margin'],20)
        self.assertEqual(metrics['current_ratio'],2)
        self.assertEqual(ev['operating_income']['source'],'SEC CompanyFacts derived')
    def test_no_operating_margin_without_expenses(self):
        f=facts({'Revenues':100,'NetIncomeLoss':10,'StockholdersEquity':50,'GrossProfit':45})
        metrics,_=annual_fields(f,date(2026,11,23))
        self.assertIsNone(metrics['operating_margin'])
    def test_current_liability_residual(self):
        f=facts({'Revenues':100,'NetIncomeLoss':10,'StockholdersEquity':50,'AssetsCurrent':80,'Liabilities':100,'LiabilitiesNoncurrent':60})
        metrics,_=annual_fields(f,date(2026,11,23))
        self.assertEqual(metrics['current_ratio'],2)

if __name__=='__main__':unittest.main()
