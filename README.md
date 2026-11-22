# USA Knowledge Graph: display fundamental ranks in memberships table

## Why the last package did not show changes
The public `main` branch version of `regional_rotation_graph.py` still has the unchanged table renderer, without an import/call to `usa_graph_membership_ranks.py`. Installing the helper file alone does nothing. A successful data workflow also does not modify the Streamlit table. This package explicitly patches the table renderer and verifies the edit.

## Install (GitHub Desktop, Windows)

1. Extract the ZIP, **open the inner `usa_graph_rank_direct_fix` directory**.
2. Copy everything inside that directory (including `scripts`, the `.py` file and the `.bat`) into the local root folder of `global-industry-cycle-intelligence` (same folder as `app.py` and `regional_rotation_graph.py`).
3. Double-click `APPLY_UPDATE_WINDOWS.bat` **inside the repository root**. You must see `SUCCESS` or `ALREADY INSTALLED` and `VERIFIED`.
4. Open GitHub Desktop. Confirm **`regional_rotation_graph.py` is modified** and **`usa_graph_membership_ranks.py` is new**. If `regional_rotation_graph.py` does not show a change and you have not previously installed it, the update has not been applied to the right repository.
5. Commit and **Push origin**. Streamlit needs the new commit.
6. Open `USA Knowledge Graph → All verified company memberships · table filters` on the deployed app. A new caption will report `USA fundamental ranking: X of Y displayed companies have a final rank`. `Final Rank`, `Total Rank`, and `Rank Status` should appear directly after `Ticker`.

The chart, graph selections, company display limits, and non-USA tables are not modified. The rank comes from `data/usa_research/fundamental_rankings.csv`, which must be present in the deployed repository. Incomplete financial companies remain unranked and sorted last.

## Troubleshooting
- No change in GitHub Desktop: you likely copied into the wrong directory or did not run the batch file.
- Ranking columns not visible, but `regional_rotation_graph.py` changed: check that GitHub `main` has the marker `USA_GRAPH_RANKING_TABLE_V2`, and redeploy Streamlit.
- Columns visible, but all ranks `N/A`: confirm `fundamental_rankings.csv` is published, and inspect the optional individual KPI section for ticker/coverage mismatches.
