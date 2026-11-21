#!/usr/bin/env python3
"""Idempotent navigation installer: does not overwrite existing app or graphs."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app.py'


def patch(source):
    if "'USA Investment Opportunity Screener'" not in source:
        marker="'USA Factors'"
        # Edit only the USA NAV_GROUPS line.
        lines=source.splitlines(keepends=True)
        candidates=[i for i,line in enumerate(lines) if "'🇺🇸 USA':" in line and "'USA Factors'" in line]
        if len(candidates)!=1:raise RuntimeError('Could not find unique USA navigation line; no change made')
        idx=candidates[0]
        lines[idx]=lines[idx].replace(marker,marker+", 'USA Investment Opportunity Screener', 'USA Company Deep Dive'",1)
        source=''.join(lines)
    if "'USA Investment Opportunity Screener': '🎯'" not in source:
        marker="PAGE_ICONS = {"
        if source.count(marker)!=1:raise RuntimeError('PAGE_ICONS location ambiguous')
        source=source.replace(marker,marker+"\n    'USA Investment Opportunity Screener': '🎯', 'USA Company Deep Dive': '🔎',",1)
    if "elif page == 'USA Investment Opportunity Screener':" not in source:
        marker="elif page == 'Data Table':"
        if source.count(marker)!=1:raise RuntimeError('Cannot find safe dispatch insertion point')
        branch=("elif page == 'USA Investment Opportunity Screener':\n"
                "    from usa_opportunity_ui import render_usa_opportunities\n"
                "    render_usa_opportunities()\n"
                "elif page == 'USA Company Deep Dive':\n"
                "    from usa_company_deep_dive_ui import render_usa_company_deep_dive\n"
                "    render_usa_company_deep_dive()\n")
        source=source.replace(marker,branch+marker,1)
    compile(source,str(APP),'exec')
    return source

if __name__=='__main__':
    old=APP.read_text(encoding='utf-8')
    new=patch(old)
    if old!=new:APP.write_text(new,encoding='utf-8');print('USA research navigation added without replacing existing pages.')
    else:print('USA research pages already installed.')
