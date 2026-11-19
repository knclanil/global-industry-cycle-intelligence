import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india_screener_statements import prepare_statement


def test_period_sorting_and_preservation():
    frame = pd.DataFrame({
        'Particulars': ['Borrowings +', 'Cash & Bank', 'Equity Capital'],
        'Mar 2025': ['(1500.5)', '12000.25', '-'],
        'TTM': ['444', '123', '0'],
        'Mar 2023': ['800', None, '90'],
        'Mar 2024': ['1,200', '45.9', '100'],
    })
    result = prepare_statement(frame, periods=2)
    assert result.columns.tolist() == ['Particulars', 'Mar 2024', 'Mar 2025']
    assert result.loc[0, 'Mar 2024'] == '1,200.00'
    assert result.loc[0, 'Mar 2025'] == '-1,500.50'
    assert result.loc[2, 'Mar 2025'] == 'N/A'
    assert result['Particulars'].tolist() == frame['Particulars'].tolist()


def test_empty_tables_no_fabrication():
    assert prepare_statement(None).empty
    assert prepare_statement(pd.DataFrame({'label':['Assets'], 'TTM':[123]})).empty


def test_multiple_periods_and_non_numeric_note():
    frame = pd.DataFrame({'Metric': ['CFO', 'Footnote'], 'Mar 23':['1,234.2', 'Reported'],
                          'Mar 24': ['2345', '—'], 'Mar 25': ['3456', '']})
    out = prepare_statement(frame, periods=0)
    assert out.columns.tolist() == ['Particulars', 'Mar 23', 'Mar 24', 'Mar 25']
    assert out.loc[1, 'Mar 23'] == 'Reported'
    assert out.loc[1, 'Mar 24'] == 'N/A'
