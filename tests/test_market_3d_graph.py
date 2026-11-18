import sys, types
sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))
sys.modules.setdefault("streamlit.components", types.ModuleType("streamlit.components"))
sys.modules.setdefault("streamlit.components.v1", types.ModuleType("streamlit.components.v1"))
from market_3d_graph import graph_payload, HTML
import pandas as pd

def test_graph_excludes_companies_and_uses_real_source_membership():
    data={'Global Factors':pd.DataFrame([{'ETF':'MTUM','Sector':'Momentum','Network Score':81,'Quadrant':'Leading'}]),'Countries':pd.DataFrame([{'ETF':'SPY','Sector':'United States','Network Score':60,'Quadrant':'Improving'}])}
    graph=graph_payload(data)
    assert len(graph['nodes'])==4
    assert len(graph['links'])==2
    assert all(n['kind']!='company' for n in graph['nodes'])
    assert any(n.get('ticker')=='MTUM' for n in graph['nodes'])
    assert 'ForceGraph3D' in HTML
