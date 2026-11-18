"""Graph structure tests independent of optional Streamlit/Plotly installations."""
import ast
from pathlib import Path
import pandas as pd

source=ast.parse((Path(__file__).parents[1]/'capital_network.py').read_text())
functions=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('node','build_unified_graph','layout')]
ns={'pd':pd}
exec(compile(ast.Module(body=functions,type_ignores=[]),'<network-functions>','exec'),ns)

def rows(data):
    return pd.DataFrame([{'ETF':ticker,'Sector':label,'Network Score':80.0,'Quadrant':'Leading','Relative strength (%)':5.0,'Return (%)':3.0} for ticker,label in data])

def test_country_assets_equity_parallel_branches():
    layers={'Countries':rows([('SPY','United States'),('INDA','India'),('EWJ','Japan')]),
            'USA Assets':rows([('VTI','Equities · US'),('GLD','Gold')]),
            'India Assets':rows([('NIFTYBEES.NS','Equities · India'),('GOLDBEES.NS','Gold')]),
            'USA Sectors':rows([('XLK','Technology')]),'India Sectors':rows([('NIFTY IT','IT')]),
            'USA Factors':rows([('QUAL','Quality')]),'India Factors':rows([('MOMENTUM','Momentum')])}
    nodes,edges=ns['build_unified_graph'](layers,5)
    edge_set=set(edges)
    for country,market,eq in [('SPY','USA','VTI'),('INDA','India','NIFTYBEES.NS')]:
        assert ('root','country:'+country) in edge_set
        assert ('country:'+country,market+':assets') in edge_set
        assert (market+':assets',market+':asset:'+eq) in edge_set
        assert (market+':asset:'+eq,market+':sectors') in edge_set
        assert (market+':asset:'+eq,market+':factors') in edge_set
    assert ('USA:sectors','USA:sector:XLK') in edge_set
    assert ('USA:factors','factor:USA:QUAL') in edge_set
    assert ('India:sectors','India:sector:NIFTY IT') in edge_set
    assert ('India:factors','factor:India:MOMENTUM') in edge_set
    assert not any(n.startswith('factor:Global:') for n in nodes)
    assert not any(a=='root' and nodes[b]['kind']=='factor' for a,b in edges)
    pos=ns['layout'](nodes,edges)
    for market in ('USA','India'):
        assert pos[market+':sectors'][0]<pos[market+':factors'][0]
        assert pos[market+':sectors'][1]==pos[market+':factors'][1]
    assert ('root','country:EWJ') in edge_set
    assert not any(a=='country:EWJ' for a,b in edges)

def test_factor_companies_require_holdings_and_deduplicate():
    layers={'Countries':rows([('SPY','United States')]),'USA Assets':rows([('VTI','Equities · US')]),
            'USA Factors':rows([('QUAL','Quality'),('MTUM','Momentum')])}
    nodes,edges=ns['build_unified_graph'](layers,5)
    assert not any(v['kind']=='company' for v in nodes.values())
    holdings=pd.DataFrame([{'factor':'QUAL','company':'Example','ticker':'EX','isin':'US123','weight':3.0},
                           {'factor':'MTUM','company':'Example','ticker':'EX','isin':'US123','weight':2.0}])
    nodes,edges=ns['build_unified_graph'](layers,5,holdings)
    companies=[n for n in nodes.values() if n['kind']=='company']
    assert len(companies)==1
    assert len([1 for a,b in edges if b==companies[0]['id']])==2
