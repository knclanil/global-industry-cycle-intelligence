import ast
import unittest
from pathlib import Path
import pandas as pd

# Extract the pure table-filter helper so tests don't require Streamlit at runtime.
source = (Path(__file__).resolve().parents[1] / 'regional_rotation_graph.py').read_text()
module = ast.parse(source)
functions = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name in ('_factor_family', 'filter_company_memberships')]
namespace = {'pd': pd, 're': __import__('re'), 'FACTOR_RULES': ((r'\blow\s+volatility\b', 'Low Volatility'), (r'\bvalue\b', 'Value'), (r'\bquality\b', 'Quality'))}
exec(compile(ast.Module(body=functions, type_ignores=[]), '<helpers>', 'exec'), namespace)
f = namespace['filter_company_memberships']

class TestFilter(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
          dict(company_key='a', quadrant='Leading', kind='sector', label='Technology', source_id='1'),
          dict(company_key='a', quadrant='Improving', kind='factor', label='Nifty500 Value 50', source_id='2'),
          dict(company_key='a', quadrant='Improving', kind='factor', label='Nifty200 Value 30', source_id='3'),
          dict(company_key='b', quadrant='Leading', kind='sector', label='Banking', source_id='4'),
          dict(company_key='b', quadrant='Leading', kind='factor', label='Quality', source_id='5'),
        ])
    def test_unfiltered(self):
        self.assertEqual(len(f(self.df)), 5)
    def test_value_family(self):
        self.assertEqual(len(f(self.df, factors=['Value'])), 2)
    def test_all_selected(self):
        result=f(self.df, sectors=['Technology'], factors=['Value'], match_mode='All selected')
        self.assertEqual(set(result.company_key), {'a'})
        self.assertEqual(len(result), 3)
    def test_no_match(self):
        self.assertTrue(f(self.df, sectors=['Banking'], factors=['Value'], match_mode='All selected').empty)
    def test_rotation_only(self):
        self.assertEqual(len(f(self.df, rotations=['Leading'])), 3)
    def test_other_memberships(self):
        self.assertEqual(len(f(self.df, sectors=['Technology'], include_other_memberships=True)), 3)

if __name__ == '__main__': unittest.main()
