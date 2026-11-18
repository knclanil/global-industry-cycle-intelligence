import unittest
from datetime import date
import pandas as pd
import country_market_data as c

class CountryTests(unittest.TestCase):
    def test_universe(self):
        self.assertEqual(len(c.SECTORS), 20)
        self.assertEqual(c.BENCHMARK, 'ACWI')

    def test_relative_trend_starts_zero(self):
        dates = pd.bdate_range('2026-01-05', periods=100)
        def frame(values):
            return pd.DataFrame({'Adj Close': values}, index=dates)
        frames = {'ACWI': frame([100 + i for i in range(100)]),
                  'SPY': frame([100 + 2*i for i in range(100)])}
        trend = c.relative_trend_from_zero(frames, ['SPY'], dates[0], dates[-1])
        self.assertAlmostEqual(trend['SPY'].iloc[0], 0)
        self.assertAlmostEqual(trend['SPY'].iloc[-1], 99)

    def test_missing_benchmark_fails(self):
        report = c.validate({}, date(2026, 1, 1))
        self.assertEqual(report['status'], 'FAIL')
