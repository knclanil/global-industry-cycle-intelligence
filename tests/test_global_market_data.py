import unittest
from datetime import date
import pandas as pd
import global_market_data as global_data

class GlobalDataTests(unittest.TestCase):
    def test_acwi_zero_based_and_excess(self):
        idx = pd.bdate_range('2024-01-01', periods=100)
        def frame(prices):
            values = pd.Series(prices, index=idx)
            return pd.DataFrame({'Open': values, 'High': values, 'Low': values, 'Close': values, 'Adj Close': values, 'Volume': 100}, index=idx)
        frames = {'ACWI': frame([100+i*.1 for i in range(100)]), 'IXN': frame([100+i*.2 for i in range(100)])}
        report = global_data.validate(frames, date(2024,5,17))
        self.assertNotEqual(report['status'], 'FAIL')
        rows, _, _, first, last = global_data.calculate(frames, ['IXN'], date(2024,3,1), date(2024,5,17), '1W')
        self.assertEqual(len(rows), 1)
        trend = global_data.relative_trend_from_zero(frames, ['IXN'], first, last)
        self.assertEqual(float(trend.iloc[0]['IXN']), 0)
        self.assertAlmostEqual(float(trend.iloc[-1]['IXN']), float(rows.iloc[0]['Excess vs SPY (pp)']), places=2)
    def test_benchmark_required(self):
        self.assertEqual(global_data.validate({}, date.today())['status'], 'FAIL')
