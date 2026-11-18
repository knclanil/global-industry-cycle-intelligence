import unittest
import pandas as pd
from india_market_data import BENCHMARK, SECTORS, validate


def frame():
    idx = pd.bdate_range('2024-01-01', periods=12)
    return pd.DataFrame({'Open': 100., 'High': 101., 'Low': 99., 'Close': 100., 'Adj Close': 100., 'Volume': 0.}, index=idx)


class IndiaValidationTests(unittest.TestCase):
    def test_bad_sector_is_excluded_not_global_failure(self):
        sector = next(iter(SECTORS))
        frames = {BENCHMARK: frame(), sector: frame()}
        frames[sector].iloc[2, frames[sector].columns.get_loc('High')] = 1.
        report = validate(frames, pd.Timestamp('2024-01-16').date())
        self.assertEqual(report['status'], 'WARNING')
        self.assertNotIn(sector, frames)

    def test_incomplete_provider_row_is_dropped(self):
        sector = next(iter(SECTORS))
        frames = {BENCHMARK: frame(), sector: frame()}
        frames[sector].iloc[3] = float('nan')
        report = validate(frames, pd.Timestamp('2024-01-16').date())
        self.assertEqual(report['status'], 'WARNING')
        self.assertEqual(len(frames[sector]), 11)

    def test_invalid_benchmark_still_fails(self):
        frames = {BENCHMARK: frame()}
        frames[BENCHMARK].iloc[2, frames[BENCHMARK].columns.get_loc('High')] = 1.
        self.assertEqual(validate(frames, pd.Timestamp('2024-01-16').date())['status'], 'FAIL')
