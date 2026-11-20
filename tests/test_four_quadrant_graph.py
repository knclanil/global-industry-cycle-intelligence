import pandas as pd
from regional_rotation_graph import graph_elements, QUADRANTS


def test_each_quadrant_builds_hierarchy():
    companies = pd.DataFrame([
        {'Category': q, 'Company': f'{q} Corp', 'Ticker': q[:3], 'company_key':q,
         'Score': 2.5, 'Sector sources':'Technology', 'Factor sources':'Momentum'}
        for q in QUADRANTS
    ])
    signals = pd.DataFrame([
        {'kind':kind,'label':name,'quadrant':q,'relative_strength':1,'rs_momentum':1}
        for q in QUADRANTS
        for kind,name in (('sector','Technology'),('factor','Momentum'))
    ])
    for q in QUADRANTS:
        nodes, links = graph_elements(companies,signals,q,10)
        assert len(nodes) == 4
        assert len(links) == 4
        assert (f'q:{q}', 'i:sector:Technology') in links
        assert ('i:factor:Momentum',f'c:{q}') in links


def test_does_not_connect_unverified_source():
    companies = pd.DataFrame([{'Category':'Leading','Company':'A','Ticker':'A','company_key':'A',
                               'Score':2,'Sector sources':'Technology','Factor sources':'Unknown'}])
    signals = pd.DataFrame([{'kind':'sector','label':'Technology','quadrant':'Leading'}])
    nodes, links = graph_elements(companies,signals,'Leading',10)
    assert len(nodes) == 1
    assert not links


def test_all_quadrants_are_separate_left_to_right_lanes():
    from regional_rotation_graph import combined_graph_elements
    companies = pd.DataFrame([
        {'Category': q, 'Company': f'{q} Corp', 'Ticker': q[:3], 'company_key':q,
         'Score': 2.5, 'Sector sources':'Technology', 'Factor sources':'Momentum'}
        for q in QUADRANTS
    ])
    signals = pd.DataFrame([
        {'kind':kind,'label':name,'quadrant':q,'relative_strength':1,'rs_momentum':1}
        for q in QUADRANTS
        for kind,name in (('sector','Technology'),('factor','Momentum'))
    ])
    nodes, links = combined_graph_elements(companies, signals, QUADRANTS, 10)
    assert len(nodes) == 16
    assert len(links) == 16
    for q in QUADRANTS:
        assert (f'q:{q}', f'{q}|i:sector:Technology') in links
        assert (f'{q}|i:factor:Momentum',f'{q}|c:{q}') in links
