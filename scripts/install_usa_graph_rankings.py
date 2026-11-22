"""Idempotently attach precomputed USA ranks to the company memberships table.

Never changes graph selection, drawing, data evidence, or other markets.
Fails with a clear error if the live source structure changed.
"""
from pathlib import Path
import ast
import shutil

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'regional_rotation_graph.py'
if not p.is_file():
    raise SystemExit('ERROR: run from repository with regional_rotation_graph.py')
s = p.read_text(encoding='utf-8')
old = '        company_summary = summarize_company_memberships(table_rows)\n'
new = '''        company_summary = summarize_company_memberships(table_rows)
        # USA only: attach precomputed full-universe SEC fundamental ranks.
        # Do NOT rank just the graph-filtered subset or mutate graph controls.
        if region == "USA":
            from usa_graph_membership_ranks import load_usa_rankings, enrich_membership_summary
            usa_rankings = load_usa_rankings()
            if usa_rankings.empty:
                st.warning("USA fundamental ranking CSV not yet published; run the USA financial ranking workflow.")
            else:
                try:
                    company_summary, usa_kpi_detail, usa_rank_counts = enrich_membership_summary(
                        company_summary, usa_rankings)
                    st.caption(f"USA fundamental ranks: {usa_rank_counts['ranked']:,} of "
                               f"{usa_rank_counts['total']:,} matching companies ranked. "
                               "Unranked companies appear last. Ranks are based on the full USA "
                               "financial universe, not the selected graph cohort.")
                    with st.expander("USA company fundamentals · individual KPI ranks", expanded=False):
                        st.dataframe(usa_kpi_detail, use_container_width=True, hide_index=True)
                        st.download_button("Download matching USA financial KPI ranks",
                            data=usa_kpi_detail.to_csv(index=False).encode("utf-8"),
                            file_name=f"usa_{period}_matching_fundamental_ranks.csv", mime="text/csv",
                            key=f"kg_usa_kpi_export_{period}")
                except (ValueError, KeyError) as exc:
                    st.warning(f"USA fundamental ranking integration unavailable: {exc}")
'''
if new in s:
    print('ALREADY INSTALLED: USA fundamental ranks integrated into membership table')
elif s.count(old) != 1:
    raise SystemExit('ERROR: expected single company_summary anchor not found; no file changed.')
else:
    replacement = s.replace(old, new, 1)
    ast.parse(replacement)
    backup = p.with_suffix('.py.pre_usa_rank_backup')
    if not backup.exists():
        shutil.copy2(p, backup)
    p.write_text(replacement, encoding='utf-8')
    print('SUCCESS: regional_rotation_graph.py updated. USA membership table now sorts by Final Rank.')
