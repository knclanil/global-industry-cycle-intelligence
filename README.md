# India Asset Flow: persist actual prices (not only coverage)

## Root cause
The old job generated `india_asset_flow_coverage.csv`, which contains only ticker, count, dates, and status. The Streamlit dashboard instead uses `stored_market_data.read_market()` to load `.parquet` files from `data/market/IndiaAssets/`. The old refresh job did **not** publish those parquet files. Also, the India government bond's canonical key (`NIFTY_GSEC_10Y`) is absent from `india_asset_market_data.TICKERS`, the list the dashboard used to read snapshots.

## Install with GitHub Desktop
Copy the **contents** of this package into the root of the repository (merge `scripts/` and `.github/workflows/`, preserving paths). The included workflow automatically applies the targeted fix to `dashboard.py` during its run and publishes that change together with the price snapshots. **You do not need to run Python locally or edit dashboard.py yourself.**

Commit, push, then **Actions → Refresh India Asset Flow Diagnostics → Run workflow**. Confirm all six canonical parquet datasets appear under `data/market/IndiaAssets/` and coverage shows available series. Streamlit redeploys on the workflow's resulting commit. Click `Refresh now` to reset Streamlit's in-process price cache.

The report is a data-coverage check, not proof that actual capital inflows/outflows occurred. The dashboard uses price-rotation proxies, not measured capital flows.
