# India Overlap & Leadership — Deployment Checklist

This release adds a new navigation page **India Overlap & Leadership** under
**Factor Analysis** while preserving India NSE Constituents, Holdings Changes,
Sector & Factor Financials, India Company Financial KPIs, and the US/Global pages.

1. Unzip the archive.
2. Copy **the contents** of `nightly_build/` into your GitHub repository root.
   Keep existing files under `data/india_holdings/` including `snapshots/`,
   `history/`, `constituents.csv`, and `companies.csv`.
3. Commit and push the code changes.
4. If the existing `data/india_holdings/constituents.csv` is already tracked in
   your repository, **run** `python scripts/build_india_overlap_rankings.py`
   from the repository root to generate rankings immediately, then commit the
   five created outputs. This command is **offline** and has no API keys.
5. Otherwise, open GitHub Actions → **India NSE Constituents Refresh** → Run
   workflow. It now builds and commits all five overlap/ranking outputs after
   refreshing NSE constituent snapshots.
6. Open the deployed Streamlit sidebar → Factor Analysis →
   **India Overlap & Leadership**.

Generated data files (added by the workflow, not fabricated by the ZIP):
- `data/india_holdings/leadership_companies.csv`
- `data/india_holdings/factor_index_overlaps.csv`
- `data/india_holdings/factor_membership_patterns.csv`
- `data/india_holdings/sector_factor_overlaps.csv`
- `data/india_holdings/leadership_build_summary.json`

The membership rankings use **no NSE/Yahoo HTTP calls during page load**, do
not require any API key, and do not use Yahoo fundamentals in their scores.
Optional Yahoo financials in the ranking table still require the separate India
Company Financials Refresh workflow. Screener is linked externally only.

**Important limitation:** The ZIP cannot contain your live 328-company dataset
because the repository's generated CSV snapshots were not provided with this
request. Preserve those files when deploying. Recompute rankings from the
committed constituent data using step 4 or 5 above.
