"""Run: python -m unittest discover -s tests -v"""
import importlib.util
import pathlib
import sys
import types
import unittest
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
streamlit = types.ModuleType('streamlit')
streamlit.cache_data = lambda **kwargs: (lambda func: func)
sys.modules['streamlit'] = streamlit
sys.path.insert(0, str(ROOT))
from rotation_graph_evidence import graph_elements
spec = importlib.util.spec_from_file_location('patched_graph', ROOT/'regional_rotation_graph.py')
graph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph)


def fixture():
    sig = pd.DataFrame([
        {'quadrant':'Leading','kind':'sector','source_id':'S1','label':'Technology'},
        {'quadrant':'Lagging','kind':'sector','source_id':'S2','label':'Energy'},
        {'quadrant':'Leading','kind':'factor','source_id':'F1','label':'Nifty500 Value 50'},
        {'quadrant':'Improving','kind':'factor','source_id':'F2','label':'Nifty200 Momentum 30'},
    ])
    ed = pd.DataFrame([
        {'company_key':'A','Company':'A Co','Ticker':'A','quadrant':'Leading','kind':'sector','source_id':'S1','portfolio_id':'A1'},
        {'company_key':'A','Company':'A Co','Ticker':'A','quadrant':'Leading','kind':'factor','source_id':'F1','portfolio_id':'A2'},
        {'company_key':'A','Company':'A Co','Ticker':'A','quadrant':'Improving','kind':'factor','source_id':'F2','portfolio_id':'A3'},
        {'company_key':'B','Company':'B Co','Ticker':'B','quadrant':'Lagging','kind':'sector','source_id':'S2','portfolio_id':'B1'},
        {'company_key':'C','Company':'C Co','Ticker':'C','quadrant':'Leading','kind':'sector','source_id':'S1','portfolio_id':'C1'},
    ])
    nodes, links = graph_elements(sig, ed)
    return nodes, links, ed

class FilterTest(unittest.TestCase):
    def test_overview_has_all(self):
        nodes, links, edges = fixture()
        result = graph.filtered_membership_rows(nodes, links, edges, 'all')
        self.assertEqual(len(result), 5)

    def test_sector_multiselect_matches_company_rows(self):
        nodes, links, edges = fixture()
        focus = {'mode':'matched','companies':{'c:A','c:C'},'sources':{'i:Leading:sector:S1'}}
        result = graph.filtered_membership_rows(nodes, links, edges, focus)
        self.assertEqual(set(result.company_key), {'A','C'})
        self.assertEqual(len(result), 4) # all connected verified sources in graph

    def test_rotation_filters_out_other_sources(self):
        nodes, links, edges = fixture()
        allowed = {n['id'] for n in nodes if n['type'] in ('sector','factor') and n['quadrant']=='Leading'}
        focus = {'mode':'matched','companies':{'c:A','c:C'},'sources':{'i:Leading:sector:S1'},'allowed_sources':allowed}
        result = graph.filtered_membership_rows(nodes, links, edges, focus)
        self.assertEqual(len(result), 3)
        self.assertEqual(set(result.quadrant), {'Leading'})

    def test_table_not_capped_by_chart(self):
        nodes, links, edges = fixture()
        focus = {'mode':'matched','companies':{'c:A','c:C'},'sources':{'i:Leading:sector:S1'}}
        _sec, _fac, shown, *_ = graph._choose_visible(nodes, links, focus, 1)
        self.assertEqual(len(shown), 1)
        result = graph.filtered_membership_rows(nodes, links, edges, focus)
        self.assertEqual(set(result.company_key), {'A','C'})

    def test_navigation_order(self):
        src = (ROOT / 'app.py').read_text()
        import ast
        tree = ast.parse(src)
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NAV_GROUPS' for t in n.targets))
        nav = ast.literal_eval(assignment.value)
        for region, names in [('🇮🇳 INDIA',['India Asset Flow','India Sector','India Factors']),('🇺🇸 USA',['USA Asset Flow','USA Sector','USA Factors']),('🌍 GLOBAL',['Global Asset Flow','Global Sectors','Global Factors'])]:
            indices = [nav[region].index(x) for x in names]
            self.assertEqual(indices, sorted(indices))

if __name__=='__main__':
    unittest.main()
