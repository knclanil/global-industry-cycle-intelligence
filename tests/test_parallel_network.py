import ast
from pathlib import Path
import pytest
import pandas as pd
pytest.importorskip('streamlit')
pytest.importorskip('plotly')
from capital_network import build_unified_graph, layout

def rows(pairs):
    return pd.DataFrame([dict(ETF=t,Sector=n,Quadrant='Leading',**{'Network Score':90-i,'Relative strength (%)':2.,'Return (%)':3.}) for i,(t,n) in enumerate(pairs)])

def test_equity_branches_parallel_and_not_global():
    layers={'Countries':rows([('SPY','United States'),('INDA','India')]),'USA Assets':rows([('VTI','Equities · US'),('GLD','Gold')]),'USA Sectors':rows([('XLK','Technology')]),'USA Factors':rows([('QUAL','Quality')]),'India Assets':rows([('NIFTYBEES.NS','Equities · India')]),'India Sectors':rows([('IT','IT')]),'India Factors':rows([('MOM','Momentum')])}
    nodes,edges=build_unified_graph(layers,5)
    assert ('root','country:SPY') in edges
    assert ('country:SPY','USA:assets') in edges
    assert ('USA:assets','USA:asset:VTI') in edges
    assert ('USA:asset:VTI','USA:sectors') in edges
    assert ('USA:asset:VTI','USA:factors') in edges
    assert ('USA:sectors','USA:sector:XLK') in edges
    assert ('USA:factors','factor:USA:QUAL') in edges
    assert ('USA:asset:VTI','USA:asset:GLD') not in edges
    pos=layout(nodes,edges)
    assert pos['USA:sectors'][0]<pos['USA:asset:VTI'][0]<pos['USA:factors'][0]

def test_company_only_from_holdings():
    layers={'Countries':rows([('SPY','United States')]),'USA Assets':rows([('VTI','Equities · US')]),'USA Factors':rows([('QUAL','Quality')])}
    n,e=build_unified_graph(layers,5)
    assert not any(v['kind']=='company' for v in n.values())
    h=pd.DataFrame([{'factor':'QUAL','company':'Example Inc','ticker':'EX','isin':'US123','weight':2.}])
    n,e=build_unified_graph(layers,5,h)
    assert ('factor:USA:QUAL','company:isin:US123') in e
