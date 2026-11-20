import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from capital_network_model import build_model, global_breadth_score, filter_model, to_graph, validate_model


def seed(tmp_path):
    pd.DataFrame([{'ETF':'SPY','Quadrant':'Leading','As of':'2026-11-20','Relative strength (%)':'3.2','RS momentum (pp)':'0.4'},
                  {'ETF':'INDA','Quadrant':'Improving'}]).to_csv(tmp_path/'country_3m_rotations.csv',index=False)
    for region in ('usa','india','global'):
        pd.DataFrame([{'source_id':'s1','kind':'sector','label':'Technology','quadrant':'Leading'},
                      {'source_id':'f1','kind':'factor','label':'Momentum','quadrant':'Weakening'},
                      {'source_id':'f2','kind':'factor','label':'Quality','quadrant':'Improving'}]).to_csv(tmp_path/f'{region}_3m_signals.csv',index=False)
        pd.DataFrame([{'source_id':'s1','kind':'sector','company_key':'alpha','Company':'Alpha','Ticker':'AAA'},
                      {'source_id':'f1','kind':'factor','company_key':'alpha','Company':'Alpha','Ticker':'AAA'},
                      {'source_id':'f2','kind':'factor','company_key':'beta','Company':'Beta','Ticker':'BBB'}]).to_csv(tmp_path/f'{region}_3m_edges.csv',index=False)


def test_root_and_country_and_adjacent(tmp_path):
    seed(tmp_path)
    table,diag=build_model('3m',tmp_path)
    nodes,edges=to_graph(table)
    paths={(e['source'],e['target']) for e in edges}
    assert ('global','rotation:Leading') in paths
    assert ('rotation:Leading','country:usa') in paths
    assert ('country:usa','usa:sector:s1') in paths
    assert ('usa:sector:s1','usa:company:alpha') in paths
    assert ('usa:company:alpha','usa:factor:f1') in paths
    assert not validate_model(table,nodes,edges)
    assert diag['classified_countries']==2
    assert len(table.loc[table.Country.eq('Japan')])==1


def test_global_score_is_breadth_not_market_return(tmp_path):
    seed(tmp_path)
    table,_=build_model('3m',tmp_path)
    score=global_breadth_score(table)
    assert score['score']==83.3 and score['classified']==2


def test_factor_only_gap_is_explicit(tmp_path):
    seed(tmp_path)
    table,_=build_model('3m',tmp_path)
    nodes,edges=to_graph(table)
    assert nodes['country:usa:unverified-sector']['kind']=='Gap'
    assert {'source':'country:usa','target':'country:usa:unverified-sector','verified':False} in edges
    assert not any(e['source']=='usa:sector:s1' and e['target']=='usa:company:beta' for e in edges)


def test_filtering_removes_unrelated_paths(tmp_path):
    seed(tmp_path)
    table,_=build_model('3m',tmp_path)
    out=filter_model(table,countries=['India'],companies=['india:company:alpha'])
    assert set(out.Country)=={'India'}
    assert set(out.Company)=={'AAA'}
    out=filter_model(table,rotations=['Leading'])
    assert set(out.Rotation)=={'Leading'}
