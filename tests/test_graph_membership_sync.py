"""Tests for graph/table company synchronization without Streamlit installed."""
import ast
from pathlib import Path
import unittest
import pandas as pd

CODE = Path(__file__).resolve().parents[1] / 'regional_rotation_graph.py'
module = ast.parse(CODE.read_text(encoding='utf-8'))
functions = [n for n in module.body if isinstance(n, ast.FunctionDef)
             and n.name == 'memberships_for_graph_companies']
ns = {'pd': pd}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(CODE), 'exec'), ns)
select = ns['memberships_for_graph_companies']

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.edges = pd.DataFrame([
            {'company_key':'A', 'quadrant':'Lagging', 'label':'Growth', 'kind':'factor'},
            {'company_key':'A', 'quadrant':'Leading', 'label':'Value', 'kind':'factor'},
            {'company_key':'A', 'quadrant':'Improving', 'label':'Quality', 'kind':'factor'},
            {'company_key':'B', 'quadrant':'Lagging', 'label':'Growth', 'kind':'factor'},
            {'company_key':'C', 'quadrant':'Leading', 'label':'Value', 'kind':'factor'},
        ])

    def test_visible_company_cohort_preserves_all_factor_memberships(self):
        out = select(self.edges, ['A', 'B'])
        self.assertEqual(set(out.company_key), {'A', 'B'})
        self.assertEqual(set(out[out.company_key.eq('A')].label),
                         {'Growth', 'Value', 'Quality'})
        self.assertEqual(len(out), 4)

    def test_display_cap_vs_entire_graph_matches(self):
        visible = select(self.edges, ['A'])
        all_matching = select(self.edges, ['A', 'B'])
        self.assertEqual(visible.company_key.nunique(), 1)
        self.assertEqual(all_matching.company_key.nunique(), 2)

    def test_empty_cohort_and_missing_key(self):
        self.assertTrue(select(self.edges, set()).empty)
        self.assertTrue(select(pd.DataFrame({'x':[1]}), ['A']).empty)

if __name__ == '__main__':
    unittest.main()
