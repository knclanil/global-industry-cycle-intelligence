# India Asset Flow — recovery package for GitHub Desktop

This package is based on the repository's `india_asset_market_data.py` contract observed November 21, 2026. That module uses Yahoo ETF prices, the NSE Nifty 50 benchmark and an official government-bond index with a bond ETF fallback. The reported failure is five unavailable histories; its exact runtime cause isn't proved by a screenshot.

## Install with GitHub Desktop

1. Extract ZIP and copy its `india_asset_recovery.py`, `scripts/`, `tests/` and `.github/` folders into the repository root (merge folders).
2. Commit and **Push origin** in GitHub Desktop.
3. On GitHub, open Actions → **Refresh India Asset Flow Diagnostics** → Run workflow (main).
4. The workflow installs the wrapper into the existing `india_asset_market_data.py`, checks individual Yahoo histories, creates `data/dashboard_cache/india_asset_flow_coverage.csv`, and commits these changes. Then Streamlit can deploy the refreshed module.
5. If `git push` fails in Actions, enable repository Settings → Actions → General → Workflow permissions → Read and write permissions. If branch protection is enabled, a PR may be needed instead.

The original module remains intact except a small, idempotent appended wrapper. Existing index priority is retained. This does **not** fabricate pricing, use return series as capital inflows, or guarantee provider access. It also does not regenerate all of the repository's pre-existing dashboards' snapshots; those may require their own daily data-refresh workflow.

Look for `status` and `last_date` for each ticker in the coverage file. If no valid histories are available, the page should continue displaying its existing warning. A true partial-data layout improvement requires the existing Streamlit dashboard renderer to be modified separately.
