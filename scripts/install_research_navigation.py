#!/usr/bin/env python3
"""Install India+USA research navigation in the local Streamlit app, preserving unrelated code."""
import ast
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app.py'
PAGES = {
    '🇮🇳 INDIA': ['India Asset Flow', 'India Sector', 'India Factors',
                  'India Investment Opportunity Screener', 'India Company Deep Dive'],
    '🇺🇸 USA': ['USA Asset Flow', 'USA Sector', 'USA Factors',
                'USA Investment Opportunity Screener', 'USA Company Deep Dive'],
}
ICONS = {
    'India Investment Opportunity Screener': '🎯',
    'India Company Deep Dive': '🔎',
    'USA Investment Opportunity Screener': '🎯',
    'USA Company Deep Dive': '🔎',
}
ROUTES = {
    'India Investment Opportunity Screener': ('india_opportunity_ui', 'render_india_opportunities'),
    'India Company Deep Dive': ('india_company_deep_dive_ui', 'render_india_company_deep_dive'),
    'USA Investment Opportunity Screener': ('usa_opportunity_ui', 'render_usa_opportunities'),
    'USA Company Deep Dive': ('usa_company_deep_dive_ui', 'render_usa_company_deep_dive'),
}
REQUIRED = [ROOT / (module + '.py') for module, _ in ROUTES.values()]


def locate(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            if isinstance(node.value, ast.Dict):
                return node.value
    raise RuntimeError(f'Could not locate {name} dictionary in app.py')


def offset(lines, row, col):
    return sum(len(s) for s in lines[:row-1]) + len(lines[row-1].encode('utf-8')[:col].decode('utf-8'))


def patch(source):
    tree = ast.parse(source)
    nav = locate(tree, 'NAV_GROUPS')
    icons = locate(tree, 'PAGE_ICONS')
    source_lines = source.splitlines(keepends=True)
    edits = []
    labels = [ast.literal_eval(k) for k in nav.keys]
    for region, order in PAGES.items():
        if region not in labels:
            raise RuntimeError(f'No {region} navigation group; no files changed')
        value = nav.values[labels.index(region)]
        if not isinstance(value, (ast.List, ast.Tuple)):
            raise RuntimeError(f'{region} is not a static navigation list')
        original = ast.literal_eval(value)
        if region == '🇺🇸 USA':
            # Preserve any other existing USA pages; insert four research-page sequence up front.
            extra = [s for s in original if s not in order]
            new = order + extra
        else:
            # India cleanup requested: retain core three + new two; keep Graph in its own section.
            new = order
        start = offset(source_lines, value.lineno, value.col_offset)
        end = offset(source_lines, value.end_lineno, value.end_col_offset)
        edits.append((start, end, repr(new)))
    present_icons = [ast.literal_eval(k) for k in icons.keys]
    missing = {k:v for k,v in ICONS.items() if k not in present_icons}
    if missing:
        insert = offset(source_lines, icons.end_lineno, icons.end_col_offset) - 1
        edits.append((insert, insert, '\n' + ''.join(f'    {k!r}: {v!r},\n' for k, v in missing.items())))
    for start, end, text in sorted(edits, reverse=True):
        source = source[:start] + text + source[end:]
    # Dispatch branch must be before fallback `else` and must work for any APP baseline.
    marker = "elif page == 'Data Table':"
    if marker not in source:
        raise RuntimeError('Could not find Data Table dispatch branch; no files changed')
    for label,(module,func) in ROUTES.items():
        branch = f"elif page == {label!r}:"
        if branch not in source:
            source = source.replace(marker, f"{branch}\n    from {module} import {func}\n    {func}()\n" + marker, 1)
    compile(source, str(APP), 'exec')
    check_tree=ast.parse(source)
    nav_dict=ast.literal_eval(locate(check_tree,'NAV_GROUPS'))
    icon_dict=ast.literal_eval(locate(check_tree,'PAGE_ICONS'))
    for region, order in PAGES.items():
        if nav_dict[region][:5] != order:
            raise RuntimeError('Navigation verification failed')
    for region, values in nav_dict.items():
        for item in values:
            if item not in icon_dict:
                raise RuntimeError(f'Missing sidebar icon for {item!r} in group {region}')
    for label in ROUTES:
        if source.count(f"elif page == {label!r}:") != 1:
            raise RuntimeError(f'Duplicate or missing dispatch for {label}')
    return source


def main():
    parser = argparse.ArgumentParser(description='Add USA/India screener and deep dive to app.py.')
    parser.add_argument('--check', action='store_true', help='Validate without writing')
    args=parser.parse_args()
    missing=[p.name for p in REQUIRED if not p.is_file()]
    if missing: raise SystemExit('Missing required UI files: ' + ', '.join(missing))
    if not APP.is_file():raise SystemExit('app.py not found. Run from your copied repository.')
    original=APP.read_text(encoding='utf-8-sig')
    updated=patch(original)
    if args.check:
        print('PASS: all four routes, icons, navigation and UI modules validated.')
    elif original==updated:
        print('ALREADY INSTALLED: no change to app.py. Commit/push any uncommitted files.')
    else:
        APP.write_text(updated,encoding='utf-8')
        print('SUCCESS: updated app.py. India and USA research pages are now in navigation.')
        print('NEXT: review app.py and 6 UI modules in GitHub Desktop; COMMIT and PUSH origin.')

if __name__=='__main__':
    main()
