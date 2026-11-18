import pandas as pd
from holdings_intelligence import display_strategy


def test_factor_labels():
    assert display_strategy('iShares MSCI USA Min Vol Factor ETF', 'USA Factor') == 'Minimum Volatility'
    assert display_strategy('iShares S&P 500 Value ETF', 'USA Factor') == 'Value'
    assert display_strategy('iShares Global Tech ETF', 'Global Sector') == 'Technology'
