"""Generate legacy financial-source inventory without deleting shared dependencies."""
from pathlib import Path
import json, re
root=Path(__file__).resolve().parent
items=[]
for p in root.rglob('*'):
    if not p.is_file() or '.git' in p.parts or p.suffix not in ('.py','.yml','.yaml'):
        continue
    try: text=p.read_text(encoding='utf-8')
    except UnicodeError: continue
    hits=[s for s in ('sec_financials','refresh_usa_company_fundamentals','build_usa_research','fundamental_rankings.csv','data/sec_cache','financial_research_ui') if s in text]
    if hits: items.append({'file':str(p.relative_to(root)),'references':hits})
report={'legacy_references':items,'deletions_performed':0,'reason':'Live MongoDB cutover and all downstream consumers not yet verified'}
(root/'MIGRATION_DEPENDENCY_AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'references':len(items),'deletions':0}))
