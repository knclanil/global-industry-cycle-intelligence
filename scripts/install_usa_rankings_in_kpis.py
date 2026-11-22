#!/usr/bin/env python3
"""Idempotently insert rankings into existing USA Financial KPIs, preserving all tabs."""
from pathlib import Path
import ast
import shutil
ROOT=Path(__file__).resolve().parents[1]
file=ROOT/'company_kpi_metrics.py'
if not file.exists():raise SystemExit('Missing company_kpi_metrics.py in repository root')
source=file.read_text(encoding='utf-8')
needle="    st.title('🇺🇸 USA Company Financial KPI Intelligence')"
addition="\n    from usa_fundamental_rankings_ui import render_usa_fundamental_rankings\n    render_usa_fundamental_rankings()\n    st.divider()"
if 'render_usa_fundamental_rankings()' in source:
    print('ALREADY INSTALLED — USA KPI rankings present')
elif source.count(needle)!=1:
    raise SystemExit('SAFE STOP: expected USA KPI title anchor not found once; no files modified')
else:
    revised=source.replace(needle,needle+addition,1)
    ast.parse(revised)
    backup=file.with_suffix('.py.before_fundamental_rankings.bak')
    if not backup.exists():shutil.copy2(file,backup)
    file.write_text(revised,encoding='utf-8')
    print('SUCCESS: inserted rankings into USA Financial KPIs without removing existing content')
