import unittest
from datetime import date
import pandas as pd
import global_factor_market_data as gf
import usa_factor_market_data as uf
import india_factor_market_data as inf

class FactorDataTests(unittest.TestCase):
    @staticmethod
    def frame(index, slope):
        values = pd.Series([100+i*slope for i in range(len(index))], index=index)
        return pd.DataFrame({k: values for k in ('Open','High','Low','Close','Adj Close')}).assign(Volume=100)

    def test_factor_rotation_and_zero_start(self):
        idx = pd.bdate_range('2024-01-01', periods=150)
        for mod in (gf, uf, inf):
            ticker = next(iter(mod.SECTORS))
            frames = {mod.BENCHMARK: self.frame(idx, .1), ticker: self.frame(idx, .2)}
            report = mod.validate(frames, date(2024,7,20))
            self.assertNotEqual(report['status'], 'FAIL', mod.__name__)
            rows, _, _, first, last = mod.calculate(frames, [ticker], date(2024,4,1), date(2024,7,20), '1W')
            self.assertEqual(len(rows), 1, mod.__name__)
            self.assertEqual(rows.iloc[0]['Sector'], mod.SECTORS[ticker])
            trend = mod.relative_trend_from_zero(frames, [ticker], first, last)
            self.assertEqual(float(trend.iloc[0][ticker]), 0)
            self.assertAlmostEqual(float(trend.iloc[-1][ticker]), float(rows.iloc[0]['Excess vs SPY (pp)']), places=2)

    def test_benchmark_required(self):
        for mod in (gf, uf, inf):
            self.assertEqual(mod.validate({}, date.today())['status'], 'FAIL')
