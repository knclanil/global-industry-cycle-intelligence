import unittest
from datetime import date
import numpy as np
import pandas as pd
from market_data import TICKERS, LOOKBACKS, calculate, validate


def synthetic():
    idx = pd.bdate_range('2024-01-01', periods=440)
    frames = {}
    for i, ticker in enumerate(TICKERS):
        close = pd.Series(100 * (1 + (0.0004 + i * 0.00002)) ** np.arange(len(idx)), index=idx)
        frames[ticker] = pd.DataFrame({'Open': close, 'High': close * 1.01,
                                       'Low': close * .99, 'Close': close,
                                       'Adj Close': close, 'Volume': 10000}, index=idx)
    return frames, idx


class MarketDataTests(unittest.TestCase):
    def test_valid_input_passes(self):
        frames, idx = synthetic()
        self.assertEqual(validate(frames, idx[-1].date())['status'], 'PASS')

    def test_invalid_high_blocks(self):
        frames, idx = synthetic()
        frames['XLK'].loc[idx[5], 'High'] = 0.1
        self.assertEqual(validate(frames, idx[-1].date())['status'], 'FAIL')

    def test_missing_session_blocks(self):
        frames, idx = synthetic()
        frames['XLK'] = frames['XLK'].drop(idx[20])
        self.assertEqual(validate(frames, idx[-1].date())['status'], 'FAIL')

    def test_all_relative_windows(self):
        frames, idx = synthetic()
        for lookback in LOOKBACKS:
            rows, rs, mom, first, last = calculate(frames, ['XLK'], idx[350].date(), idx[-1].date(), lookback)
            self.assertEqual(len(rows), 1)
            self.assertIn(rows.iloc[0]['Quadrant'], ['Leading','Improving','Weakening','Lagging'])


if __name__ == '__main__':
    unittest.main()
