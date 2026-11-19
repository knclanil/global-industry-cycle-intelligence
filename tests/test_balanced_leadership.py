import pandas as pd
from holdings_intelligence import rank_companies

def position(pid, category, name, weight=5):
    return dict(portfolio_id=pid, category=category, issuer_id=name, company=name,
                ticker=name, weight=weight, as_of='2026-11-18', fund_title=category,
                group='USA Factor' if category == 'factor' else 'USA Sector')

def test_balance_penalty_changes_order():
    d=pd.DataFrame([position('s1','sector','BAL'), position('f1','factor','BAL'),
                    position('s2','sector','SKEW'),position('f2','factor','SKEW')])
    ranked,_=rank_companies(d,performance_scores={'s1':70,'f1':70,'s2':100,'f2':45})
    assert ranked.iloc[0].company == 'BAL'
    assert ranked.iloc[0].consistency_penalty == 0
    assert ranked.iloc[1].consistency_penalty == 11
    assert ranked.iloc[0]['rank'] == 1

def test_missing_dimension_unranked_not_zero():
    d=pd.DataFrame([position('s1','sector','ONLY'),position('s2','sector','BOTH'),
                    position('f1','factor','BOTH')])
    ranked,_=rank_companies(d,performance_scores={'s1':95,'s2':60,'f1':60})
    only=ranked.set_index('company').loc['ONLY']
    assert only.coverage_status == 'Insufficient Coverage'
    assert pd.isna(only.final_score) and pd.isna(only['rank'])
    assert ranked.iloc[0].company == 'BOTH'

def test_missing_etf_scores_flag_partial():
    d=pd.DataFrame([position('s1','sector','A'),position('s2','sector','A'),
                    position('f1','factor','A')])
    ranked,_=rank_companies(d,performance_scores={'s1':80,'f1':80})
    assert ranked.iloc[0].balanced_eligible
    assert ranked.iloc[0].performance_status == 'Partial'

def test_region_isolation():
    d=pd.DataFrame([position('s1','sector','USA'),position('f1','factor','USA'),
                    position('g1','global_sector','GLOBAL'),position('g2','global_factor','GLOBAL')])
    scores={'s1':80,'f1':80,'g1':60,'g2':60}
    usa,_=rank_companies(d,performance_scores=scores)
    globe,_=rank_companies(d,factor_category='global_factor',sector_category='global_sector',performance_scores=scores)
    assert usa.company.tolist()==['USA'] and globe.company.tolist()==['GLOBAL']
    assert usa.iloc[0].final_score > globe.iloc[0].final_score
