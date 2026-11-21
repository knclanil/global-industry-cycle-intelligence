"""Offline regression tests; no Yahoo network requests are made."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline', ROOT/'scripts'/'india_financial_pipeline_v2.py')
pipeline=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

class TestIndiaFinancialPipeline(unittest.TestCase):
    def test_canonical_aliases_preserve_real_values(self):
        pipeline.install_normalization_compatibility()
        sheet=pd.DataFrame({'2025-03-31':[1400,190]},index=['totalRevenue','netIncome'])
        out=pipeline.data.normalize_sheet(sheet, {'revenue','net_income'})
        self.assertEqual(out['2025-03-31']['revenue'],1400)
        self.assertEqual(out['2025-03-31']['net_income'],190)

    def test_absent_stays_missing(self):
        sheet=pd.DataFrame({'2025-03-31':[1400]},index=['RandomMetric'])
        out=pipeline.data.normalize_sheet(sheet, {'revenue'})
        self.assertEqual(out,{})

    def test_audit_counts_only_usable_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            companies=root/'companies.csv'
            companies.write_text('company_key,symbol,company_name\nISIN:X,ABC,ABC LTD\nISIN:Y,XYZ,XYZ LTD\n')
            output=root/'financials'
            doc={'company_key':'ISIN:X','symbol':'ABC','company_name':'ABC LTD','currency':'INR',
                 'quote':{'price':100,'market_cap':10000,'currency':'INR'},
                 'statements':{'annual':{'income':{'2025-03-31':{'revenue':1500,'net_income':100,'diluted_eps':5}},
                                         'balance':{'2025-03-31':{'equity':500,'total_assets':800}},'cashflow':{}},'quarterly':{}}}
            dest=pipeline.data.company_file('ISIN:X',output)
            dest.parent.mkdir(parents=True)
            dest.write_text(json.dumps(doc))
            report=pipeline.audit(companies,output)
            self.assertEqual(report['universe'],2)
            self.assertEqual(report['coverage']['snapshot'],1)
            self.assertEqual(report['coverage']['fundamental_ready'],1)
            self.assertEqual(report['coverage']['valuation_ready'],1)
            self.assertEqual(report['metric_coverage']['free_cash_flow'],0)
            self.assertTrue((output/'kpi_coverage_by_company.csv').exists())

if __name__=='__main__':
    unittest.main()
