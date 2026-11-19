import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india_screener_statements import prepare_source_table


def test_shareholding_percent_preserved():
    df = pd.DataFrame({'Particulars': ['Promoters', 'FIIs'], 'Mar 2024': ['55.90%', '12.10%'], 'Mar 2025': ['56.70%', '13.00%']})
    result = prepare_source_table(df, periods=1)
    assert result.columns.tolist() == ['Particulars', 'Mar 2025']
    assert result.loc[0, 'Mar 2025'] == '56.70%'


def test_peers_preserved():
    df = pd.DataFrame({'Name': ['Company A', 'Median'], 'P/E': [12.5, 19.2], 'CMP Rs.': [190, 240]})
    result = prepare_source_table(df, periods=1)
    assert result.columns.tolist() == ['Name', 'P/E', 'CMP Rs.']
    assert result.loc[1, 'P/E'] == '19.2'


def test_quarterly_ordering():
    df = pd.DataFrame({'Particulars': ['Sales'], 'Dec 2025': ['200'], 'Jun 2025': ['100'], 'Sep 2025': ['120']})
    result = prepare_source_table(df, periods=2, financial=True)
    assert result.columns.tolist() == ['Particulars', 'Sep 2025', 'Dec 2025']


def test_parser_all_source_tables():
    import types
    if "streamlit" not in sys.modules:
        stub = types.ModuleType("streamlit")
        stub.cache_data = lambda *a, **kw: (lambda f: f)
        sys.modules["streamlit"] = stub
    from india_valuation_reference import parse_tables
    def section(name, label):
        return f'<section id="{name}"><table><thead><tr><th>Particulars</th><th>Mar 2025</th></tr></thead><tbody><tr><td>{label}</td><td>120</td></tr></tbody></table></section>'
    body = ''.join(section(k, k) for k in ['quarters', 'profit-loss', 'balance-sheet', 'cash-flow', 'ratios', 'shareholding', 'peers'])
    result = parse_tables('<html><body>'+body+'</body></html>')
    assert set(result) >= {'Quarterly Results','Profit & Loss','Balance Sheet', 'Cash Flows', 'Ratios', 'Shareholding Pattern', 'Peer Comparison'}
