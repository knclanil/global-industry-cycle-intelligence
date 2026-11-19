import io
import pandas as pd
import pytest
from holdings_constituent_utils import parse_holdings,score_holdings

def test_parse_csv_and_weights():
    f=io.BytesIO(b'Company Name,Weight (%),Ticker\nAlpha,2.5%,AAA\nBeta,1.2%,BBB\n');f.name='x.csv'
    d=parse_holdings(f,factor='Value')
    assert len(d)==2 and d.weight.sum()==pytest.approx(3.7)

def test_consensus_breadth_and_rank():
    d=pd.DataFrame([
        ['Value','Alpha','AAA',4.0],['Value','Beta','BBB',1.0],
        ['Momentum','Alpha','AAA',3.0],['Momentum','Gamma','GGG',2.0],
    ],columns=['factor','company','ticker','weight'])
    d['isin']='';d['as_of']='';d['source']='test'
    scores,detail=score_holdings(d,['Value','Momentum'])
    assert scores.iloc[0].Company=='Alpha'
    assert scores.iloc[0]['Factor Count']==2
    assert scores.iloc[0]['Breadth Score']==100
    assert scores.iloc[0]['Top-10 Count']==2
    assert scores['Consensus Score'].between(0,100).all()
    top,_=score_holdings(d,['Value','Momentum'],'Top 10 only')
    assert len(top)==3

def test_missing_factor_excluded_by_caller():
    d=pd.DataFrame([{'factor':'Value','company':'Alpha','ticker':'AAA','isin':'','weight':2.,'as_of':'','source':''}])
    scores,_=score_holdings(d,['Value'])
    assert scores.iloc[0]['Breadth Score']==100

def test_duplicate_security_rejected():
    d=pd.DataFrame([{'factor':'Value','company':'Alpha','ticker':'AAA','isin':'','weight':2.,'as_of':'','source':''}]*2)
    with pytest.raises(ValueError,match='Duplicate'):score_holdings(d,['Value'])

def test_overweight_rejected():
    d=pd.DataFrame([{'factor':'Value','company':'Alpha','ticker':'AAA','isin':'','weight':103.,'as_of':'','source':''}])
    with pytest.raises(ValueError,match='102'):score_holdings(d,['Value'])
