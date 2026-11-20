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


def test_one_network_with_four_rotations_and_shared_company():
    from regional_rotation_graph import combined_graph_elements
    companies = pd.DataFrame([
        {'Category': q, 'Company': 'Shared Corp', 'Ticker': 'SHR', 'company_key':'shared',
         'Score': 2.5, 'Sector sources':'Technology', 'Factor sources':'Momentum'}
        for q in QUADRANTS
    ])
    signals = pd.DataFrame([
        {'kind':kind,'label':name,'quadrant':q,'relative_strength':1,'rs_momentum':1}
        for q in QUADRANTS
        for kind,name in (('sector','Technology'),('factor','Momentum'))
    ])
    nodes, links = combined_graph_elements(companies, signals, QUADRANTS, 10)
    assert len([n for n in nodes if n['type'] == 'rotation']) == 4
    assert len([n for n in nodes if n['type'] == 'company']) == 1
    assert len([n for n in nodes if n['type'] in ('sector','factor')]) == 8
    for q in QUADRANTS:
        assert (f'q:{q}', f'{q}|i:sector:Technology') in links
        assert (f'{q}|i:factor:Momentum', 'c:shared') in links


def test_empty_data_still_has_four_rotation_nodes():
    from regional_rotation_graph import combined_graph_elements
    nodes, links = combined_graph_elements(pd.DataFrame(), pd.DataFrame(), QUADRANTS, 10)
    assert len(nodes) == 4
    assert not links
