import pandas as pd
from holdings_intelligence import normalize, rank_companies, ranking_display_table

def test_source_country_sector_in_independent_global_leadership():
    raw=pd.DataFrame([{'Ticker':'AAPL','Name':'APPLE','Sector':'Information Technology',
                       'Location':'United States','Asset Class':'Equity','Weight (%)':'15.05'}])
    holdings=normalize(raw,'271538','2026-11-17','iShares Global Quality ETF')
    assert holdings.iloc[0]['country']=='United States'
    assert holdings.iloc[0]['sector']=='Information Technology'
    ranking,_=rank_companies(holdings,factor_ids=['271538'],factor_category='global_factor',sector_category='global_sector')
    display=ranking_display_table(ranking,holdings,'Global')
    assert display.iloc[0]['Country']=='United States'
    assert display.iloc[0]['Sector']=='Information Technology'
    assert 'portfolio_id' not in display.columns
