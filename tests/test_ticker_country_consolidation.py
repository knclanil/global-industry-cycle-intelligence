import pandas as pd
import pytest
from holdings_intelligence import normalize

def test_consolidate_and_suffix():
    rows=pd.DataFrame([
      dict(Ticker='SREN',Name='SWISS RE',Location='Switzerland',Sector='Financials',**{'Asset Class':'Equity','Weight (%)':'1.25'}),
      dict(Ticker='SREN',Name='SWISS RE',Location='Switzerland',Sector='Financials',**{'Asset Class':'Equity','Weight (%)':'0.01'}),
      dict(Ticker='SAN',Name='SANTANDER',Location='Spain',Sector='Financials',**{'Asset Class':'Equity','Weight (%)':'1.52'}),
      dict(Ticker='SAN',Name='SANOFI',Location='France',Sector='Health Care',**{'Asset Class':'Equity','Weight (%)':'1.43'}),
    ])
    result=normalize(rows,'271540','2026-11-17')
    assert len(result)==3
    assert result.loc[result.ticker=='SREN','weight'].iloc[0]==pytest.approx(1.26)
    assert set(result.ticker)=={'SREN','SAN-ES','SAN-FR'}
    assert result.issuer_id.nunique()==3

def test_same_country_different_names_is_not_silently_merged():
    rows=pd.DataFrame({'Ticker':['ABC','ABC'],'Name':['FIRST','SECOND'], 'Location':['Japan','Japan'],'Weight (%)':[1,2]})
    with pytest.raises(ValueError,match='Conflicting companies'):
        normalize(rows,'271540','2026-11-17')
