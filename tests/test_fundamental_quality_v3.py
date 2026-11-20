import numpy as np
import pandas as pd
from fundamental_rankings_engine import history_metrics, rank_fundamentals, DIMENSION_WEIGHTS, FINANCIAL_DIMENSION_WEIGHTS


def make_company(i, sector='Industrial'):
    history=[]
    for year in range(2021, 2026):
        income = 8. + i + (year - 2021)
        rev = 100. + 10 * (year - 2021) + i
        history.append({'date':f'{year}-03-31','revenue':rev,'net_income':income,
                        'operating_income':30+i,'equity':100,'debt':20+i,
                        'current_assets':100,'current_liabilities':50,
                        'assets':300,'liabilities':80,'dividend':2+year-2021,
                        'operating_cash_flow':25+i,'capital_expenditure':6,
                        'weighted_average_shares':10})
    return dict(Region='India',Sector=sector,Ticker=str(i),Company=str(i), **history_metrics(history))


def test_weights_and_observed_history():
    assert np.isclose(sum(DIMENSION_WEIGHTS.values()), 1)
    assert np.isclose(sum(FINANCIAL_DIMENSION_WEIGHTS.values()), 1)
    r=make_company(2)
    assert r['FCF observations']==5
    assert r['FCF margin']>0
    assert np.isfinite(r['EPS CAGR'])
    assert np.isfinite(r['Revenue CAGR'])


def test_quality_domains_and_no_fake_snapshot_rank():
    frame=pd.DataFrame([make_company(i) for i in range(8)])
    result=rank_fundamentals(frame)
    assert result['Fundamental score'].notna().sum()==8
    assert result['Fundamental score'].between(0,100).all()
    assert result['Growth quality score'].notna().all()
    assert result['Cash flow quality score'].notna().all()
    fake=frame.iloc[:1].copy()
    fake['History']=[[]]
    fake['Years']=0
    result=rank_fundamentals(fake)
    assert result['Fundamental score'].isna().all()


def test_no_data_reweighting():
    frame=pd.DataFrame([make_company(i) for i in range(8)])
    for row in frame.index:
        frame.loc[row,'operating_cash_flow']=np.nan
    result=rank_fundamentals(frame)
    assert (result['Fundamental score'].dropna() <= 100).all()


def test_banks_use_separate_model():
    banks=pd.DataFrame([make_company(i,'Banking') for i in range(8)])
    result=rank_fundamentals(banks)
    assert 'Cash flow quality score' not in result or result['Cash flow quality score'].isna().all()
    assert result['Financial institution'].all()
