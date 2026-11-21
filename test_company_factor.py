import sys
import types
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from rotation_graph_evidence import build_membership_edges, graph_elements


def test_unclassified_growth_company_membership(monkeypatch):
    engine = types.ModuleType('leading_lagging_engine')
    engine.source_signal_mapping = lambda region, holdings, signals: ({}, [{'Source':'Nifty500 Growth 50', 'Reason':'No verified matching rotation signal'}])
    expansion = types.ModuleType('india_index_rotation_expansion')
    expansion.SOURCE_TICKERS = {'nifty500_growth_50': 'NSE_INDEX:nifty500_growth_50'}
    monkeypatch.setitem(sys.modules, 'leading_lagging_engine', engine)
    monkeypatch.setitem(sys.modules, 'india_index_rotation_expansion', expansion)
    holdings = pd.DataFrame([{'index_slug':'nifty500_growth_50', 'company_key':'INE001', 'company_name':'Example Ltd', 'symbol':'EXAMPLE.NS'},
                             {'index_slug':'nifty500_growth_50', 'company_key':'INE001', 'company_name':'Example Ltd', 'symbol':'EXAMPLE.NS'}])
    signals = pd.DataFrame([{'kind':'sector','source_id':'^CNXIT','label':'Technology','quadrant':'Leading'}])
    edges, unmapped = build_membership_edges('India', holdings, signals)
    assert len(edges) == 1
    assert edges.iloc[0]['quadrant'] == 'Unavailable'
    assert edges.iloc[0]['label'] == 'Growth'
    nodes, links = graph_elements(signals, edges)
    assert ('i:Unavailable:factor:NSE_INDEX:nifty500_growth_50', 'c:INE001') in links
    assert not any(a.startswith('q:') and 'Unavailable' in b for a,b in links)
    assert len([n for n in nodes if n['type']=='company']) == 1
