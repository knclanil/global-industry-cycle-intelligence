from scripts.refresh_holdings import parse_document
from holdings_intelligence import normalize


def test_market_weight_header_239725():
    text = '''iShares S&P 500 Value ETF\nFund Holdings as of,17-Nov-26\nTicker,Name,Type,Sector,Asset Class,Market Value,Market Weight,Notional Weight\nAAPL,APPLE,EQUITY,Information Technology,Equity,"4,208,795,036.42",8.52,8.49\nAMZN,AMAZON.COM INC,EQUITY,Consumer Discretionary,Equity,"1,949,953,225.98",3.95,3.94\n'''
    df, date = parse_document(text.encode())
    assert date == '2026-11-17'
    assert df['Weight (%)'].tolist() == ['8.52', '3.95']


def test_duplicate_ticker_different_names_kept_separate_239710():
    import pandas as pd
    df = pd.DataFrame({'Ticker':['XYZ','XYZ','ABC'],'Name':['COMPANY A','COMPANY B','COMPANY C'],
                       'Weight (%)':[20,30,50], 'Asset Class':['Equity']*3})
    out = normalize(df,'239710','2026-11-17')
    assert len(out)==3
    assert out.issuer_id.nunique()==3
    assert out.weight.sum()==100
