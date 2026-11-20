import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rotation_graph_evidence import graph_elements, QUADRANTS


def test_all_quadrants_and_orphan_signals():
    signals = pd.DataFrame([
        {'quadrant':q, 'kind':'sector' if i % 2 == 0 else 'factor',
         'source_id':f'S{i}', 'label':f'Signal {i}'}
        for i,q in enumerate(QUADRANTS)
    ])
    edges = pd.DataFrame([
        {'company_key':'same-company','Company':'Acme','Ticker':'ACME',
         'quadrant':'Improving','kind':'factor','source_id':'S1'},
        {'company_key':'same-company','Company':'Acme','Ticker':'ACME',
         'quadrant':'Weakening','kind':'sector','source_id':'S2'},
    ])
    nodes, links = graph_elements(signals, edges)
    assert sum(n['type']=='rotation' for n in nodes)==4
    assert sum(n['type'] in ('sector','factor') for n in nodes)==4
    assert sum(n['type']=='company' for n in nodes)==1
    assert ('i:Improving:factor:S1','c:same-company') in links
    assert ('i:Weakening:sector:S2','c:same-company') in links
    assert ('q:Leading','i:Leading:sector:S0') in links
    assert ('q:Lagging','i:Lagging:factor:S3') in links


def test_no_unverified_company_links():
    signals=pd.DataFrame([{'quadrant':'Leading','kind':'sector',
                          'source_id':'S','label':'Technology'}])
    edges=pd.DataFrame([{'company_key':'x','Company':'X','Ticker':'X',
                         'quadrant':'Improving','kind':'factor','source_id':'UNKNOWN'}])
    nodes, links=graph_elements(signals, edges)
    assert all(n['type'] != 'company' for n in nodes)
    assert len(links)==1
