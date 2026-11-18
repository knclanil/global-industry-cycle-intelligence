import pandas as pd
from holdings_intelligence import rank_companies

def row(pid, cat, company, weight):
    return dict(portfolio_id=pid, category=cat, issuer_id=company, company=company,
                ticker=company, weight=weight, as_of='2026-11-17', fund_title=cat,
                group='USA Factor' if cat=='factor' else 'USA Sector')

def test_leading_beats_lagging_despite_smaller_weight():
    data=pd.DataFrame([row('239505','sector','LEAD',4),row('239505','sector','LAG',8),
                       row('239695','factor','LEAD',4),row('239695','factor','LAG',8),
                       row('239506','sector','LEAD',4),row('239506','sector','LAG',8)])
    # Scores are ETF-level, not company-level: both companies have identical exposure
    # to each ETF; stronger weight should rank first, as intended.
    scores={'239505':90,'239695':90,'239506':20}
    ranked,_=rank_companies(data, performance_scores=scores)
    assert ranked.iloc[0].company=='LAG'
    assert ranked.iloc[0].etf_count==3
    assert ranked.iloc[0].performance_status=='Verified'

def test_leader_in_leading_etfs_outweighs_more_lagging_etfs():
    data=pd.DataFrame([row('239505','sector','LEAD',5),row('239695','factor','LEAD',5),
                       row('239506','sector','LAG',5),row('239511','sector','LAG',5),
                       row('239728','factor','LAG',5)])
    scores={'239505':95,'239695':90,'239506':15,'239511':20,'239728':25}
    ranked,_=rank_companies(data, performance_scores=scores)
    assert ranked.iloc[0].company=='LEAD'
    assert ranked.iloc[0].etf_count < ranked.iloc[1].etf_count

def test_missing_performance_not_zero():
    data=pd.DataFrame([row('239505','sector','A',5)])
    ranked,_=rank_companies(data, performance_scores={})
    assert ranked.iloc[0].performance_status=='Missing'
    assert ranked.iloc[0].base_score==50
    assert pd.isna(ranked.iloc[0].sector_alignment)

def test_usa_global_isolation():
    data=pd.DataFrame([row('239505','sector','USA',5),row('239750','global_sector','GLOBAL',5)])
    usa,_=rank_companies(data, performance_scores={'239505':90,'239750':10})
    globe,_=rank_companies(data, factor_category='global_factor', sector_category='global_sector', performance_scores={'239505':90,'239750':10})
    assert usa.company.tolist()==['USA']
    assert globe.company.tolist()==['GLOBAL']
