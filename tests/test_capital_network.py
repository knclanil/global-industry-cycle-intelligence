import pytest
pytest.importorskip("streamlit")
pytest.importorskip("plotly")
import pandas as pd
from capital_network import score_rows, build_graph, make_figure

def rows(names):
    return score_rows(pd.DataFrame([{'ETF':t,'Sector':name,'Quadrant':'Leading','Relative strength (%)':i+1.,'RS momentum (pp)':i+2.,'Return (%)':3.} for i,(t,name) in enumerate(names)]))

def test_peer_scores_bounded():
    d=rows([('A','Alpha'),('B','Beta')]);assert d['Network Score'].between(0,100).all()

def test_country_graph_has_country_assets_and_sectors():
    layers={'Countries':rows([('SPY','United States'),('INDA','India')]),'USA Assets':rows([('VTI','Equities · US')]),'USA Sectors':rows([('XLK','Technology')])}
    n,e=build_graph('Country → assets → sectors → companies','Global',layers,5)
    assert any(v['kind']=='sector' for v in n.values());assert len(e)>=3
    assert len(make_figure(n,e).data)>0

def test_company_nodes_require_real_holdings():
    layers={'Global Assets':rows([('VT','Equities · Global')]),'USA Factors':rows([('QUAL','Quality')])}
    n,e=build_graph('Assets → equity → factors → companies','USA',layers,5)
    assert not any(v['kind']=='company' for v in n.values())
    holdings=pd.DataFrame([{'factor':'QUAL','company':'Example Corp','ticker':'EX','isin':'US0000000001','weight':2.1}])
    n,e=build_graph('Assets → equity → factors → companies','USA',layers,5,holdings)
    assert any(v['kind']=='company' for v in n.values())
