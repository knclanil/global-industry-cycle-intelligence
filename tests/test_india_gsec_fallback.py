from datetime import date
import pandas as pd
import india_asset_market_data as assets
import data_table

START, END = date(2026, 1, 1), date(2026, 1, 9)

def frame():
    idx = pd.date_range('2026-01-02', periods=4, freq='B')
    return pd.DataFrame({'Open':[100,101,102,103], 'High':[102,103,104,105],
                         'Low':[99,100,101,102], 'Close':[101,102,103,104],
                         'Adj Close':[101,102,103,104], 'Volume':[0]*4}, index=idx)

def test_index_preferred_to_etf():
    result, errors = assets._government_bond_history(START, END, frame(),
        python_history=lambda *args: frame(), direct_history=lambda *args: (_ for _ in ()).throw(AssertionError()))
    assert result.attrs['instrument_type'] == 'Government bond index'
    assert result.attrs['fallback_used'] == 'No'
    assert result.attrs['return_basis'] == 'Price index (not total return)'

def test_etf_fallback_and_audit_metadata():
    def unavailable(*args): raise ValueError('not available')
    result, errors = assets._government_bond_history(START, END, frame(),
        python_history=unavailable, direct_history=unavailable)
    assert result.attrs['underlying_symbol'] == 'SETF10GILT.NS'
    assert result.attrs['fallback_used'] == 'Yes'
    rows = data_table.raw_rows({assets.GSEC_KEY: result})
    assert set(rows['Fallback used']) == {'Yes'}
    assert set(rows['Underlying symbol']) == {'SETF10GILT.NS'}
    assert errors

def test_missing_sources_do_not_fabricate_prices():
    def unavailable(*args): raise ValueError('not available')
    result, errors = assets._government_bond_history(START, END, None,
        python_history=unavailable, direct_history=unavailable)
    assert result is None and errors
