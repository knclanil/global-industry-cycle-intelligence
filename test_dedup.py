import sys, types
st = types.ModuleType('streamlit')
st.cache_data = lambda **kwargs: lambda f: f
sys.modules['streamlit'] = st
import regional_rotation_graph as g

def test_names():
    assert g._factor_family('Nifty500 Value 50') == 'Value'
    assert g._factor_family('Nifty200 Value 30') == 'Value'
    assert g._factor_family('Nifty100 Low Volatility 30') == 'Low Volatility'
    assert g._factor_family('Nifty200 Momentum 30') == 'Momentum'
    assert g._factor_family('Nifty500 Growth 50') == 'Growth'
    assert g._factor_family('Nifty Alpha 50') == 'Alpha'

def test_group_keeps_index_evidence():
    src=[{'id':'i:Leading:factor:one','label':'Nifty500 Value 50','type':'factor','quadrant':'Leading'},
         {'id':'i:Improving:factor:two','label':'Nifty200 Value 30','type':'factor','quadrant':'Improving'},
         {'id':'i:Lagging:factor:three','label':'Nifty500 Growth 50','type':'factor','quadrant':'Lagging'}]
    groups, mapping=g._collapse_sources(src)
    assert len(groups)==2
    value=next(n for n in groups if n['label']=='Value')
    assert set(value['quadrants'])=={'Leading','Improving'}
    assert len(value['raw_sources'])==2
    assert mapping[src[0]['id']]==mapping[src[1]['id']]
    assert mapping[src[2]['id']]!=mapping[src[1]['id']]
