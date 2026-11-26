"""Offline checks for the aggregate-only distribution."""
from pathlib import Path
import ast, csv
ROOT=Path(__file__).resolve().parent
PAGES={'Global Knowledge Graph','USA Knowledge Graph','India Knowledge Graph','Global Countries','Global Asset Flow','Global Sectors','Global Factors','USA Asset Flow','USA Sectors','USA Factors','India Asset Flow','India Sectors','India Factors','Market Intelligence Wiki'}
source=(ROOT/'app.py').read_text()
for name in PAGES: assert repr(name) in source or f'"{name}"' in source, name
for name in ('maketdata_bridge.py','maketdata_ui.py','sec_financials.py','company_financial_research.py'):
 assert not (ROOT/name).exists(),name
for forbidden in ('data/fundamentals','data/holdings','data/usa_research','data/india_financials'):
 assert not (ROOT/forbidden).exists(),forbidden
assert not (ROOT/'.github/workflows/build-dashboard-cache.yml').exists(), 'legacy cache writer must be removed'
assert not (ROOT/'data/dashboard_cache/india_companies.csv').exists()
assert (ROOT/'wiki_page.py').exists()
assert (ROOT/'india_asset_recovery.py').exists()
for p in ROOT.rglob('*.py'):
 ast.parse(p.read_text(),filename=str(p))
for region in ('global','usa','india'):
 for period in ('1m','3m','6m'):
  p=ROOT/f'data/dashboard_cache/rotation_graphs/{region}_{period}_signals.csv'
  assert p.exists(),p
  with p.open(newline='') as f:
   rows=list(csv.DictReader(f))
  assert rows,p
  assert all(r['kind'].lower() in ('sector','factor') for r in rows),p
for market in ('Countries','Global','GlobalAssets','GlobalFactors','USA','USAAssets','USAFactors','India','IndiaAssets','IndiaFactors'):
 assert (ROOT/'data/market'/market).is_dir(),market
print('PASS: 14 navigation pages, 9 aggregate graph snapshots, 10 market folders, no selected forbidden modules, Python syntax')
