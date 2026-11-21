#!/usr/bin/env python3
"""Idempotent, fail-closed UI integration into existing India financials page."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/'india_financial_ui.py'

def patch(text):
    if "with tabs[5]:\n        from india_opportunity_ui import render_india_opportunities" in text:
        return text
    anchor="tabs = st.tabs(['Sector & thematic', 'Factor families', 'All source indices', 'Sector × factor matrix', 'Coverage & diagnostics'])"
    replacement="tabs = st.tabs(['Sector & thematic', 'Factor families', 'All source indices', 'Sector × factor matrix', 'Coverage & diagnostics', 'Investment Opportunities'])"
    if text.count(anchor)!=1:
        raise RuntimeError('Current india_financial_ui.py tab definition differs; refusing unsafe edit. No file was modified.')
    text=text.replace(anchor,replacement)
    # add one more tab to render function after existing final lines; it has no trailing functions in current repo.
    # The appended block is indented four spaces, remaining within render_india_sector_factor_financials().
    text=text.rstrip()+"\n    with tabs[5]:\n        from india_opportunity_ui import render_india_opportunities\n        render_india_opportunities()\n"
    compile(text,str(FILE),'exec')
    return text

if __name__=='__main__':
    if not FILE.exists():raise SystemExit(f'Missing {FILE}')
    before=FILE.read_text(encoding='utf-8')
    after=patch(before)
    if after!=before:
        FILE.write_text(after,encoding='utf-8')
        print('Updated existing India financial page with Investment Opportunities tab.')
    else:print('Already integrated; no changes.')
