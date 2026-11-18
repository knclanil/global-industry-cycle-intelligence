from scripts.refresh_holdings import parse_document

HEADER='Ticker,Name,Sector,Asset Class,Weight (%)\nABC,Example Inc,Technology,Equity,2.5\n'

def test_reference_project_inline_date():
    data=('iShares Test ETF\nFund Holdings as of Nov 17, 2026\n\n'+HEADER).encode()
    frame,date=parse_document(data)
    assert date=='2026-11-17' and frame.iloc[0]['Weight (%)']=='2.5'

def test_reference_project_alternate_headers_and_utf16():
    data=('iShares Test ETF\nFund Holdings as of,"17-Nov-2026"\n\nSymbol,Security Name,Asset Class,Weight Percent\nABC,Example Inc,Equity,2.5\n').encode('utf-16')
    frame,date=parse_document(data)
    assert date=='2026-11-17' and frame.iloc[0]['Ticker']=='ABC'

def test_never_trust_missing_effective_date():
    try: parse_document(HEADER.encode())
    except ValueError as e: assert 'date' in str(e)
    else: raise AssertionError('Missing issuer effective date accepted')
