# India Asset Flow — integrated data pipeline

This package replaces the fragmented India Asset Flow diagnostics-only job.
It uses the existing NSE-first market source logic and Yahoo fallback, saves actual
Parquet price snapshots, validates the **same** snapshots used in Streamlit,
then publishes the histories, `sources.json`, and coverage report together.

## Install with GitHub Desktop

1. Extract ZIP. Open GitHub Desktop → Repository → Show in Explorer/Finder.
2. Copy the `scripts` and `.github` folders from the ZIP into the repository;
   merge folders and replace only matching files. **Do not delete other files.**
3. Commit the new files and push `main`.
4. In GitHub → Actions choose **Refresh India Asset Flow (prices and validation)**
   → Run workflow on main. Wait until the run completes successfully.
5. Check `data/market/IndiaAssets/` for six Parquet files and `sources.json`.
   Check `data/dashboard_cache/india_asset_flow_coverage.csv` for diagnostics.
   Then open Streamlit → India Asset Flow → Refresh now.

## What the one-time integration does

`scripts/install_india_asset_pipeline.py` applies **two small and idempotent**
source fixes in the GitHub Actions checkout and the workflow publishes them:
- `dashboard.py`: loads canonical `NIFTY_GSEC_10Y` from stored Parquet instead
  of trying to read the raw ETF fallback `SETF10GILT.NS`.
- `scripts/incremental_refresh.py`: writes canonical bond key during other
  scheduled market refreshes, avoiding the old mismatch.

If the corresponding source lines have changed upstream, the job fails clearly
rather than overwriting unrelated code. Later runs do not change these files.

## Important caveats

- India Asset Flow is **relative price rotation**, not actual capital inflows.
- If official government-bond index history is unavailable, the bond ETF can
  be used as a *different price proxy*, with its source disclosed. The code does
  not splice index and ETF observations during a single provider request.
- Existing `india_asset_market_data.py` includes the recovery wrapper. The
  scheduled job calls its `download` only once.
- A green job means saved history loads and at least one 3M rotation computes.
  It does NOT guarantee every asset is available; consult coverage CSV.
- Changes are not automatically deployed by this ZIP; GitHub Desktop push and
  a successful GitHub Actions run are required.
