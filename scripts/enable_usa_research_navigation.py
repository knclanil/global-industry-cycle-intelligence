"""Idempotently register existing USA research pages in the current Streamlit app.

Only app.py is changed. No graph, market, holdings, or pipeline code is touched.
"""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.py'
USA_GROUP_OLD = "'🇺🇸 USA': ['USA Asset Flow', 'USA Sector', 'USA Factors', 'USA Analysis'],"
USA_GROUP_NEW = "'🇺🇸 USA': ['USA Asset Flow', 'USA Sector', 'USA Factors', 'USA Investment Opportunity Screener', 'USA Company Deep Dive'],"
ICON_ANCHOR = "    'India Investment Opportunity Screener': '🎯', 'India Company Deep Dive': '🔎',"
ICON_INSERT = "    'USA Investment Opportunity Screener': '🎯', 'USA Company Deep Dive': '🔎',\n"
ROUTE_ANCHOR = "elif page == 'India Investment Opportunity Screener':"
ROUTE_INSERT = """elif page == 'USA Investment Opportunity Screener':
    from usa_opportunity_ui import render_usa_opportunities
    render_usa_opportunities()
elif page == 'USA Company Deep Dive':
    from usa_company_deep_dive_ui import render_usa_company_deep_dive
    render_usa_company_deep_dive()
"""

def patch(src):
    if USA_GROUP_NEW not in src:
        if src.count(USA_GROUP_OLD) != 1:
            raise RuntimeError('Cannot find exact current USA navigation. No changes made.')
        src = src.replace(USA_GROUP_OLD, USA_GROUP_NEW, 1)
    if "'USA Investment Opportunity Screener': '🎯'" not in src:
        if src.count(ICON_ANCHOR) != 1:
            raise RuntimeError('Cannot find exact icon anchor. No changes made.')
        src = src.replace(ICON_ANCHOR, ICON_INSERT + ICON_ANCHOR, 1)
    if "elif page == 'USA Investment Opportunity Screener':" not in src:
        if src.count(ROUTE_ANCHOR) != 1:
            raise RuntimeError('Cannot find exact route anchor. No changes made.')
        src = src.replace(ROUTE_ANCHOR, ROUTE_INSERT + ROUTE_ANCHOR, 1)
    ast.parse(src)
    for required in ['USA Investment Opportunity Screener', 'USA Company Deep Dive']:
        if src.count(required) < 3:
            raise RuntimeError(f'Page registration appears incomplete: {required}')
    return src

def main():
    for name, fn in [('USA screener', 'usa_opportunity_ui.py'), ('USA company deep dive', 'usa_company_deep_dive_ui.py'), ('USA research data', 'usa_research_data.py')]:
        if not (ROOT / fn).exists():
            raise SystemExit(f'MISSING {name}: {fn}. Cannot enable navigation safely.')
    old = APP.read_text(encoding='utf-8')
    new = patch(old)
    if new != old:
        APP.write_text(new, encoding='utf-8')
        print('SUCCESS: app.py updated; USA research pages are registered.')
    else:
        print('ALREADY INSTALLED: USA research pages are already registered in app.py.')
    print('Commit app.py and push origin using GitHub Desktop.')

if __name__ == '__main__':
    main()
