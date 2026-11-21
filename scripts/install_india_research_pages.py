#!/usr/bin/env python3
"""Fail-closed, idempotent sidebar integration preserving the rest of app.py."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app.py'
ENTRIES="'India Asset Flow', 'India Sector', 'India Factors'"
NEW_ENTRIES=ENTRIES + ", 'India Investment Opportunity Screener', 'India Company Deep Dive'"


def patch(source):
    if "'India Investment Opportunity Screener', 'India Company Deep Dive'" not in source:
        anchor="'🇮🇳 INDIA': ["+ENTRIES+"]"
        if source.count(anchor)!=1:
            raise RuntimeError('India sidebar layout differs from cleanup baseline; refusing unsafe modification.')
        source=source.replace(anchor,"'🇮🇳 INDIA': ["+NEW_ENTRIES+"]")
    if "'India Investment Opportunity Screener': '🎯'" not in source:
        anchor="    'India Sector & Factor Financials': '📈',"
        if source.count(anchor)!=1:raise RuntimeError('PAGE_ICONS anchor missing; refusing unsafe modification')
        source=source.replace(anchor,anchor+"\n    'India Investment Opportunity Screener': '🎯', 'India Company Deep Dive': '🔎',")
    if "elif page == 'India Investment Opportunity Screener':" not in source:
        anchor="elif page == 'India Sector & Factor Financials':"
        if source.count(anchor)!=1:raise RuntimeError('India dispatch anchor missing; refusing unsafe modification')
        branch=("elif page == 'India Investment Opportunity Screener':\n"
                "    from india_opportunity_ui import render_india_opportunities\n"
                "    render_india_opportunities()\n"
                "elif page == 'India Company Deep Dive':\n"
                "    from india_company_deep_dive_ui import render_india_company_deep_dive\n"
                "    render_india_company_deep_dive()\n")
        source=source.replace(anchor,branch+anchor)
    compile(source,str(APP),'exec')
    return source


if __name__=='__main__':
    if not APP.is_file():raise SystemExit('Missing app.py')
    original=APP.read_text(encoding='utf-8')
    revised=patch(original)
    if revised!=original:
        APP.write_text(revised,encoding='utf-8')
        print('Added two India research pages. Existing navigation and graph unchanged.')
    else:print('Research pages already installed; no changes.')
