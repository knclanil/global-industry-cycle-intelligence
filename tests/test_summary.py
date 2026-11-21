import ast
from pathlib import Path
import re
import pandas as pd

SOURCE = Path(__file__).resolve().parents[1] / 'regional_rotation_graph.py'
tree = ast.parse(SOURCE.read_text())
names = {'summarize_company_memberships', '_factor_family'}
subset = ast.Module(body=[n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Assign)) and (
    isinstance(n, ast.FunctionDef) and n.name in names or
    isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FACTOR_RULES' for t in n.targets)
)], type_ignores=[])
ns = {'pd': pd, 're': re}
exec(compile(subset, str(SOURCE), 'exec'), ns)
summarize = ns['summarize_company_memberships']


def test_one_row_preserves_multiple_quadrants_and_families():
    rows = pd.DataFrame([
        {'company_key':'a', 'Company':'ALPHA LTD', 'Ticker':'ALP', 'quadrant':'Leading','kind':'sector','label':'Technology','mapping_method':'exact','source_id':'XLK','portfolio_id':'1','weight':2},
        {'company_key':'a', 'Company':'ALPHA LTD', 'Ticker':'ALP', 'quadrant':'Lagging','kind':'factor','label':'Nifty500 Value 50','mapping_method':'category_proxy','source_id':'VAL','portfolio_id':'2','weight':4},
        {'company_key':'a', 'Company':'ALPHA LTD', 'Ticker':'ALP', 'quadrant':'Improving','kind':'factor','label':'Nifty200 Value 30','mapping_method':'category_proxy','source_id':'VAL2','portfolio_id':'3','weight':6},
        {'company_key':'a', 'Company':'ALPHA LTD', 'Ticker':'ALP', 'quadrant':'Leading','kind':'sector','label':'Technology','mapping_method':'exact','source_id':'XLK','portfolio_id':'1','weight':2},
        {'company_key':'b', 'Company':'BETA LTD', 'Ticker':'BET', 'quadrant':'Weakening','kind':'factor','label':'Momentum','mapping_method':'official','source_id':'MOM','portfolio_id':'4','weight':None},
    ])
    got = summarize(rows)
    assert list(got.columns) == ['Company', 'Ticker', 'Quadrant', 'Sector', 'Factor', 'Mapping', 'Weight', 'Avg Weight']
    assert len(got) == 2
    a = got[got['Ticker']=='ALP'].iloc[0]
    assert a['Quadrant'] == 'Improving · Lagging · Leading'
    assert a['Sector'] == 'Technology'
    assert a['Factor'] == 'Value'
    assert a['Avg Weight'] == 4
    assert a['Weight'] == '2.00% · 4.00% · 6.00%'
    b = got[got['Ticker']=='BET'].iloc[0]
    assert b['Weight'] == 'N/A'
    assert pd.isna(b['Avg Weight'])


def test_missing_weight_and_empty():
    assert summarize(pd.DataFrame()).empty
    rows = pd.DataFrame([{'company_key':'c','Company':'C','Ticker':'C','kind':'factor','label':'Quality','weight':-1}])
    assert summarize(rows)['Weight'][0] == 'N/A'
