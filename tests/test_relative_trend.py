import unittest
import pandas as pd
from market_data import relative_trend_from_zero

class TestRelativeTrend(unittest.TestCase):
    def test_zero_base_and_excess_returns(self):
        idx = pd.bdate_range('2026-01-05', periods=3)
        frames = {'SPY': pd.DataFrame({'Adj Close': [100, 110, 120]}, index=idx),
                  'XLK': pd.DataFrame({'Adj Close': [50, 60, 60]}, index=idx),
                  'XLE': pd.DataFrame({'Adj Close': [40, 40, 40]}, index=idx)}
        result = relative_trend_from_zero(frames, ['XLK', 'XLE'], idx[0], idx[-1])
        self.assertEqual(result.iloc[0].tolist(), [0, 0])
        self.assertAlmostEqual(result['XLK'].iloc[1], 10)
        self.assertAlmostEqual(result['XLK'].iloc[2], 0)
        self.assertAlmostEqual(result['XLE'].iloc[2], -20)

if __name__ == '__main__':
    unittest.main()
