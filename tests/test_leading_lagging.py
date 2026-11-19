import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from leading_lagging_engine import classify, build_lists, rotation_signals

def test_quadrants():
    assert classify(2,2)=='Leading'
    assert classify(-2,-2)=='Lagging'
    assert classify(2,-2)=='Weakening'
    assert classify(-2,2)=='Improving'

def test_india_two_sided_evidence():
    rows=pd.DataFrame([
        {'company_key':'ISIN:A','company_name':'A','symbol':'AAA','index_slug':'nifty_bank'},
        {'company_key':'ISIN:A','company_name':'A','symbol':'AAA','index_slug':'nifty50_value_20'},
        {'company_key':'ISIN:B','company_name':'B','symbol':'BBB','index_slug':'nifty_it'},
        {'company_key':'ISIN:B','company_name':'B','symbol':'BBB','index_slug':'nifty200_quality_30'},
        {'company_key':'ISIN:C','company_name':'C','symbol':'CCC','index_slug':'nifty_bank'},
    ])
    signals=pd.DataFrame([
        {'kind':'sector','source_id':'^NIFTYBANK','label':'Bank','quadrant':'Leading','relative_strength':5,'rs_momentum':1},
        {'kind':'factor','source_id':'NIFTY50_VALUE20','label':'Value','quadrant':'Leading','relative_strength':4,'rs_momentum':1},
        {'kind':'sector','source_id':'^CNXIT','label':'IT','quadrant':'Lagging','relative_strength':-3,'rs_momentum':-1},
        {'kind':'factor','source_id':'NIFTY200_QUALITY30','label':'Quality','quadrant':'Lagging','relative_strength':-2,'rs_momentum':-1},
    ])
    result,missing=build_lists('India',rows,signals)
    assert set(result.Ticker)=={'AAA','BBB'}
    assert result[result.Ticker=='AAA'].iloc[0]['Category']=='Leading'
    assert result[result.Ticker=='BBB'].iloc[0]['Category']=='Lagging'
    assert not result.Score.isna().any()

def test_no_fabrication_without_signal():
    rows=pd.DataFrame([{'company_key':'A','company_name':'A','symbol':'AAA','index_slug':'nifty_bank'}])
    out,_=build_lists('India',rows,pd.DataFrame())
    assert out.empty
