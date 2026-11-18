import unittest
import pandas as pd
from india_market_data import _clean_provider_rows, _structurally_valid, BENCHMARK, validate


def sample():
    dates = pd.bdate_range('2025-01-01', periods=12)
    return pd.DataFrame({'Open': 100., 'High': 102., 'Low': 98., 'Close': 101., 'Adj Close': 101., 'Volume': 0.}, index=dates)


class ProviderCleaningTests(unittest.TestCase):
    def test_yahoo_placeholder_does_not_fail_nifty_benchmark(self):
        df = sample()
        df.iloc[3] = float('nan')
        clean = _clean_provider_rows(df)
        self.assertEqual(len(clean), 11)
        report = validate({BENCHMARK: clean}, pd.Timestamp('2025-01-17').date())
        self.assertNotEqual(report['status'], 'FAIL')

    def test_conflicting_duplicate_is_not_silently_removed(self):
        df = sample()
        duplicate = df.iloc[[3]].copy()
        duplicate['Close'] = 110.
        df = pd.concat([df, duplicate])
        self.assertTrue(_clean_provider_rows(df).index.has_duplicates)

    def test_invalid_nse_ohlc_rejected_for_fallback(self):
        df = sample()
        df.iloc[3, df.columns.get_loc('High')] = 50.
        self.assertFalse(_structurally_valid(df))


if __name__ == '__main__':
    unittest.main()
