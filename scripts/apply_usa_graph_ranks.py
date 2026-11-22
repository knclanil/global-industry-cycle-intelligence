"""Deterministic direct patch for the existing USA Knowledge Graph membership table.

The patch intentionally touches only table rendering, not graph choices or layout.
Run once from a repository containing regional_rotation_graph.py.
"""
from __future__ import annotations
import ast
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
source = root / 'regional_rotation_graph.py'
helper = root / 'usa_graph_membership_ranks.py'
if not source.exists() or not helper.exists():
    sys.exit('ERROR: Copy this package into repository root before running.')
s = source.read_text(encoding='utf-8')
marker = '# USA_GRAPH_RANKING_TABLE_V2'
anchor = '        company_summary = summarize_company_memberships(table_rows)\n'
addition = '''        # USA_GRAPH_RANKING_TABLE_V2
        # Enrich only the read-only table. No graph filters, nodes, or links change.
        if region == "USA":
            from usa_graph_membership_ranks import load_usa_rankings, enrich_membership_summary
            rank_data = load_usa_rankings()
            if rank_data.empty:
                st.warning("USA fundamental rankings not found. Confirm that "
                           "data/usa_research/fundamental_rankings.csv exists in the deployed repository.")
            else:
                try:
                    company_summary, usa_rank_details, rank_stats = enrich_membership_summary(
                        company_summary, rank_data)
                    st.caption(f"USA fundamental ranking: {rank_stats['ranked']:,} of "
                               f"{rank_stats['total']:,} displayed companies have a final rank; "
                               "incomplete companies remain visible at the bottom.")
                    with st.expander("USA fundamental values and individual ranks"):
                        st.dataframe(usa_rank_details, use_container_width=True, hide_index=True)
                except (KeyError, ValueError, TypeError) as exc:
                    st.error(f"USA ranking join error: {exc}")
'''
if marker in s:
    print('ALREADY INSTALLED: USA_GRAPH_RANKING_TABLE_V2 found in regional_rotation_graph.py')
else:
    count = s.count(anchor)
    if count != 1:
        sys.exit(f'ERROR: expected exactly one company summary anchor, found {count}. No changes made.')
    patched = s.replace(anchor, anchor + addition, 1)
    ast.parse(patched)
    source.write_text(patched, encoding='utf-8')
    print('SUCCESS: Modified regional_rotation_graph.py (USA graph membership table only).')

# Assertions: a visible change exists in the local file; avoids silent installer success.
final = source.read_text(encoding='utf-8')
assert final.count(marker) == 1
ast.parse(final)
print(f'VERIFIED: {source}')
print(f'VERIFIED: helper exists: {helper.name}')
rankings = root / 'data/usa_research/fundamental_rankings.csv'
print('RANKING CSV: ' + ('PRESENT' if rankings.exists() else 'MISSING (dashboard will show warning)'))
print('NEXT: GitHub Desktop -> commit BOTH changed/new Python files -> Push origin.')
