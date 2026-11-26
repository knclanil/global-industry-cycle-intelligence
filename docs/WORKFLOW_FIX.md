# GitHub Actions cache conflict fix

The old `build-dashboard-cache.yml` workflow generated company-level CSV files and committed the entire `data/dashboard_cache/` tree. After the clean replacement removed those files, its automated `git pull --rebase` conflicted with `main`.

## Applied
- Legacy dashboard-cache workflow is absent from this replacement.
- Only the aggregate market refresh workflow remains.
- The workflow stages only `data/market/` and uses a shared aggregate-writer concurrency group.
- A rebase failure aborts cleanly rather than restoring deleted company files.
- The workflow commits only when refresh steps succeed.
- `verify_clean.py` checks that legacy workflow and company cache are absent.

## Critical deployment note
Replace the *entire* repository contents, including `.github/workflows/`. Merely overlaying files will leave old workflows and scripts behind. Delete the old workflow in GitHub before rerunning.

If a previous workflow run is still in progress, cancel it in GitHub Actions. A failed workflow's temporary rebase state is isolated to that runner; it does not require running `git rebase --skip` in your local repository.

The replacement still uses simplified aggregate graph visualizations, not the original interactive knowledge-graph engine; full graph restoration and live Streamlit verification remain outstanding.
