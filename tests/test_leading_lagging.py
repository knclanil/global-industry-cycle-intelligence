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

def test_usa_sector_factor_category_proxy_populates_rankings():
    from leading_lagging_engine import source_signal_mapping
    rows = pd.DataFrame([
        {'issuer_id':'TICKER_COUNTRY:AAA|US','company':'Company AAA','ticker':'AAA','portfolio_id':'239505','fund_title':'iShares U.S. Technology ETF','weight':4.5},
        {'issuer_id':'TICKER_COUNTRY:AAA|US','company':'Company AAA','ticker':'AAA','portfolio_id':'239695','fund_title':'iShares MSCI USA Momentum Factor ETF','weight':2.0},
    ])
    signals = pd.DataFrame([
        {'kind':'sector','source_id':'XLK','label':'Technology','quadrant':'Leading','relative_strength':5,'rs_momentum':2},
        {'kind':'factor','source_id':'MTUM','label':'Momentum','quadrant':'Leading','relative_strength':4,'rs_momentum':1},
    ])
    matched,missing=source_signal_mapping('USA',rows,signals)
    assert len(matched)==2,missing
    assert all(v['mapping_method']=='category_proxy' for v in matched.values())
    result,_=build_lists('USA',rows,signals)
    assert len(result)==1 and result.iloc[0].Ticker=='AAA'
    assert result.iloc[0]['Signal basis']=='Category ETF proxy'


def test_unmapped_generic_index_not_misidentified_as_sector():
    from leading_lagging_engine import _title_proxy
    sig=pd.DataFrame([{'kind':'sector','source_id':'XLK','label':'Information Technology'}])
    assert _title_proxy('iShares Core S&P 500 ETF','sector',sig) is None


def test_usa_average_etf_weight_uses_distinct_qualifying_funds():
    rows = pd.DataFrame([
        {'issuer_id':'A|US','company':'Example A','ticker':'AAA','portfolio_id':'239505','fund_title':'iShares U.S. Technology ETF','weight':6.0},
        {'issuer_id':'A|US','company':'Example A','ticker':'AAA','portfolio_id':'239695','fund_title':'iShares MSCI USA Momentum Factor ETF','weight':2.0},
        # Duplicate membership must not inflate or dilute the average.
        {'issuer_id':'A|US','company':'Example A','ticker':'AAA','portfolio_id':'239505','fund_title':'iShares U.S. Technology ETF','weight':6.0},
    ])
    signals = pd.DataFrame([
        {'kind':'sector','source_id':'XLK','label':'Technology','quadrant':'Leading','relative_strength':5,'rs_momentum':2},
        {'kind':'factor','source_id':'MTUM','label':'Momentum','quadrant':'Leading','relative_strength':4,'rs_momentum':1},
    ])
    out,_=build_lists('USA',rows,signals)
    assert len(out)==1
    assert out.iloc[0]['Avg ETF % weight']==4.0
    assert out.iloc[0]['Exposure']==8.0


def test_india_average_etf_weight_unavailable():
    rows=pd.DataFrame([
        {'company_key':'ISIN:A','company_name':'A','symbol':'AAA','index_slug':'nifty_bank'},
        {'company_key':'ISIN:A','company_name':'A','symbol':'AAA','index_slug':'nifty50_value_20'},
    ])
    signals=pd.DataFrame([
        {'kind':'sector','source_id':'^NIFTYBANK','label':'Bank','quadrant':'Leading','relative_strength':5,'rs_momentum':1},
        {'kind':'factor','source_id':'NIFTY50_VALUE20','label':'Value','quadrant':'Leading','relative_strength':4,'rs_momentum':1},
    ])
    out,_=build_lists('India',rows,signals)
    assert len(out)==1
    assert pd.isna(out.iloc[0]['Avg ETF % weight'])
