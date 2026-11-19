import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from fundamental_intelligence import extract_company_facts, resolve_us_company, score_profiles

def test_cik_requires_name_match():
    directory = pd.DataFrame([{'ticker':'ABC','title':'ALPHA TECHNOLOGIES INC','cik_str':42}])
    assert resolve_us_company('ABC','ALPHA TECHNOLOGIES',directory)==42
    assert resolve_us_company('ABC','UNRELATED INSURANCE GROUP',directory) is None

def test_no_quarter_in_annual_revenue():
    payload={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[
        {'form':'10-K','fp':'FY','start':'2024-01-01','end':'2024-12-31','filed':'2025-02-01','val':100,'accn':'a'},
        {'form':'10-Q','fp':'Q1','start':'2025-01-01','end':'2025-03-31','filed':'2025-04-01','val':400,'accn':'b'},
        {'form':'10-K/A','fp':'FY','start':'2024-01-01','end':'2024-12-31','filed':'2025-03-01','val':110,'accn':'c'}]}}}}}
    df=extract_company_facts(payload)
    assert len(df)==1 and df.iloc[0].revenue==110
    assert df.iloc[0].revenue_accession=='c'

def test_no_peers_no_score():
    frame=pd.DataFrame([{'sector':'Technology','roe':.2,'operating_margin':.2,'net_margin':.2,
        'revenue_growth':.1,'earnings_growth':.1,'net_debt':100,'fcf_margin':.1,'cash_conversion':1.0}])
    result=score_profiles(frame)
    assert pd.isna(result.iloc[0].fundamental_score)
    assert result.iloc[0].status=='Insufficient coverage'
