from holdings_intelligence import GLOBAL_FACTORS, GROUPS, ALL_SOURCES, display_strategy, normalize
import pandas as pd

def test_five_global_factors_registered():
    assert set(GLOBAL_FACTORS)=={'271538','275382','239499','239605','271540'}
    assert all(GROUPS[pid]=='Global Factor' and ALL_SOURCES[pid]=='global_factor' for pid in GLOBAL_FACTORS)
    assert len(ALL_SOURCES)==33

def test_global_factor_label_and_normalization():
    assert display_strategy('iShares MSCI World Momentum Factor ETF','Global Factor')=='Momentum'
    frame=pd.DataFrame([{'Ticker':'ABC','Name':'Example Inc','Asset Class':'Equity','Weight (%)':'2.4'}])
    result=normalize(frame,'271538','2026-11-17','iShares Global Quality Factor ETF')
    assert result.group.iloc[0]=='Global Factor'
    assert result.fund_title.iloc[0]=='iShares Global Quality Factor ETF'
