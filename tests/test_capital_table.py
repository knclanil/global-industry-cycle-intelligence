"""Run with pytest after installing repository requirements."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capital_network import build_capital_table, filter_table, make_graph
import pandas as pd


def test_canonical_paths(tmp_path):
    pd.DataFrame([
        {'ETF':'SPY','Quadrant':'Leading'},
        {'ETF':'INDA','Quadrant':'Improving'},
    ]).to_csv(tmp_path / 'country_3m_rotations.csv', index=False)
    for region in ('usa', 'india', 'global'):
        pd.DataFrame([
            {'source_id':'s1','kind':'sector','label':'Technology','quadrant':'Leading'},
            {'source_id':'f1','kind':'factor','label':'Momentum','quadrant':'Weakening'},
        ]).to_csv(tmp_path/f'{region}_3m_signals.csv',index=False)
        pd.DataFrame([
            {'source_id':'s1','kind':'sector','company_key':'a','Company':'Alpha','Ticker':'AAA'},
            {'source_id':'f1','kind':'factor','company_key':'a','Company':'Alpha','Ticker':'AAA'},
        ]).to_csv(tmp_path/f'{region}_3m_edges.csv',index=False)
    table, diag = build_capital_table('3m', tmp_path)
    row = table[(table.Country=='United States')&(table.Company=='AAA')].iloc[0]
    assert (row.Rotation, row.Sector, row.Factor) == ('Leading', 'Technology', 'Momentum')
    assert row.sector_rotation == 'Leading' and row.factor_rotation == 'Weakening'
    assert len(table.loc[table.Country.isin(['Japan'])]) == 1
    assert table.loc[table.Country=='Japan','Sector'].iloc[0] == ''
    nodes, edges = make_graph(table)
    assert ('rotation:Leading','country:USA') in edges
    assert ('country:USA','USA:sector:s1') in edges
    assert ('USA:sector:s1','USA:a') in edges
    assert ('USA:a','USA:factor:f1') in edges
    assert ('rotation:Global scope','country:Global') in edges
    rank = {'Global':0,'Rotation':1,'Country':2,'Sector':3,'Company':4,'Factor':5}
    assert all(rank[nodes[b]['kind']] - rank[nodes[a]['kind']] == 1 for a,b in edges)
    filtered = filter_table(table, countries=['India'], sectors=['India:sector:s1'])
    assert set(filtered.Country)=={'India'}
    assert filtered.loc[filtered.Company=='AAA','Factor'].iloc[0]=='Momentum'


def test_no_invented_connections(tmp_path):
    table, _ = build_capital_table('1m', tmp_path)
    nodes, edges = make_graph(table)
    assert len([e for e in edges if e[0]=='country:EWJ']) == 0
    assert ('rotation:Unclassified','country:EWJ') in edges
