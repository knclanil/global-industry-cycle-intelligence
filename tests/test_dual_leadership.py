import pandas as pd
from holdings_intelligence import rank_companies, GLOBAL_FACTORS, ranking_display_table

def sample(pid, category, issuer, weight):
    return dict(portfolio_id=pid,category=category,issuer_id=issuer,company=issuer,ticker=issuer,weight=weight,as_of='2026-11-17',fund_title=category,group='Global Factor' if category=='global_factor' else 'Global Sector')

def test_global_scoring_includes_global_sector_and_excludes_usa():
    d=pd.DataFrame([sample('271538','global_factor','ABC',4),sample('239750','global_sector','ABC',10),sample('271538','global_factor','XYZ',1),sample('239750','global_sector','XYZ',1)])
    rank, changes=rank_companies(d, factor_ids=GLOBAL_FACTORS,factor_category='global_factor',sector_category='global_sector',performance_scores={'271538':80,'239750':80})
    assert len(rank)==2
    assert rank.iloc[0].company=='ABC'
    assert rank.iloc[0].sector_leader
    assert rank.iloc[0].base_score>rank.iloc[1].base_score
    view=ranking_display_table(rank,d,'Global')
    assert 'Global Factor Funds' in view and 'Global Sector Funds' in view
    assert 'portfolio_id' not in view

def test_usa_global_independence():
    d=pd.DataFrame([sample('271538','global_factor','GLOBAL',4),sample('239750','global_sector','GLOBAL',5),sample('239695','factor','USA',4),sample('239505','sector','USA',5)])
    usa,_=rank_companies(d[d.category.isin(['factor','sector'])])
    world,_=rank_companies(d[d.category.isin(['global_factor','global_sector'])],factor_ids=GLOBAL_FACTORS,factor_category='global_factor',sector_category='global_sector')
    assert usa.company.tolist()==['USA']
    assert world.company.tolist()==['GLOBAL']
