from scripts.refresh_holdings import parse_document
from holdings_intelligence import GROUPS, normalize

def test_title_from_first_cell_and_group():
    blob=b'iShares Global Tech ETF\nFund Holdings as of,17-Nov-26\nTicker,Name,Sector,Asset Class,Weight (%)\nAAPL,APPLE,Information Technology,Equity,15.05\nNVDA,NVIDIA,Information Technology,Equity,11.02\n'
    frame, asof=parse_document(blob)
    assert frame.attrs['fund_title']=='iShares Global Tech ETF'
    assert asof=='2026-11-17'
    result=normalize(frame,'239750',asof,frame.attrs['fund_title'])
    assert result.group.iloc[0]=='Global Sector'
    assert result.fund_title.iloc[0]=='iShares Global Tech ETF'

def test_all_sources_are_grouped():
    assert len(GROUPS)==33
    assert set(GROUPS.values())=={'USA Factor','USA Sector','Global Factor','Global Sector'}
