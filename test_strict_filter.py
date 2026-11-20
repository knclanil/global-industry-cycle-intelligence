import sys, types, importlib.util
from pathlib import Path
if 'streamlit' not in sys.modules:
    try:
        import streamlit
    except ImportError:
        stub=types.ModuleType('streamlit');stub.cache_data=lambda **kw: lambda f:f
        sys.modules['streamlit']=stub
spec=importlib.util.spec_from_file_location('cap',Path(__file__).parent/'capital_network.py')
cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)

def fixture():
    nodes={'root':{'kind':'root','label':'GLOBAL'}}
    for country in ('USA','India','EWJ'):
        nodes['country:'+country]={'kind':'country','label':country,'country':country}
    for scope, sector, company, factor, quadrant in (
        ('USA','tech','A','quality','Leading'),
        ('India','finance','B','value','Lagging')):
        nodes[f'{scope}:sector:{sector}']={'kind':'sector','country':scope,'quadrant':quadrant,'label':sector}
        nodes[f'{scope}:company:{company}']={'kind':'company','country':scope,'label':company}
        nodes[f'{scope}:factor:{factor}']={'kind':'factor','country':scope,'quadrant':quadrant,'label':factor}
    edges=[('root','country:USA'),('root','country:India'),('root','country:EWJ'),
           ('country:USA','USA:sector:tech'),('USA:sector:tech','USA:company:A'),('USA:company:A','USA:factor:quality'),
           ('country:India','India:sector:finance'),('India:sector:finance','India:company:B'),('India:company:B','India:factor:value')]
    return nodes, edges

def test_filtered_country_disappears_unrelated():
    nodes,edges=fixture(); visible, kept, companies, count=cap._select(nodes,edges,chosen_countries=['USA'])
    assert companies=={'USA:company:A'} and count==1
    assert 'country:India' not in visible and 'country:EWJ' not in visible
    assert 'India:sector:finance' not in visible
    assert all(a in visible and b in visible for a,b in kept)

def test_factor_selection_hides_unrelated():
    nodes,edges=fixture(); visible, kept, companies, count=cap._select(nodes,edges,chosen_factors=['USA:factor:quality'])
    assert companies=={'USA:company:A'}
    assert 'India:company:B' not in visible and 'country:India' not in visible
    assert 'USA:sector:tech' in visible

def test_unverified_country_node_only():
    nodes,edges=fixture(); visible, kept, companies, count=cap._select(nodes,edges,chosen_countries=['EWJ'])
    assert visible=={'root','country:EWJ'} and count==0

def test_country_and_sector_are_intersection():
    nodes,edges=fixture(); visible, kept, companies, count=cap._select(nodes,edges,chosen_countries=['India'],chosen_sectors=['USA:sector:tech'])
    assert companies==set() and count==0
    assert 'USA:company:A' not in visible

def test_default_keeps_all_countries():
    nodes,edges=fixture();visible, *_=cap._select(nodes,edges)
    assert {'country:USA','country:India','country:EWJ'}<=visible

if __name__=='__main__':
    for name,fn in list(globals().items()):
        if name.startswith('test_'): fn();print('PASS',name)
