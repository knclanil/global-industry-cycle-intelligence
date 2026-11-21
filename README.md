# Fix: GitHub Actions cannot rebase because of unstaged changes

Replace `.github/workflows/refresh-india-asset-flow.yml` with the file in this package.

The job's recovery installer edits `india_asset_market_data.py`. Other generated or modified files may remain unstaged. The old publication step committed only two paths and then rebased the dirty build checkout, which caused `cannot rebase: You have unstaged changes`.

The replacement publishes only the intended application module and coverage CSV from a clean temporary Git worktree. It retries on non-fast-forward pushes and does not force-push. If someone edits the application module concurrently, it stops instead of overwriting their work.

## GitHub Desktop

1. Extract this ZIP.
2. Open Repository > Show in Explorer.
3. Copy `.github/workflows/refresh-india-asset-flow.yml` from ZIP into the identical path in your repository.
4. Commit and Push origin in GitHub Desktop.
5. Open GitHub Actions > Refresh India Asset Flow Diagnostics > Run workflow.

**Important:** This workflow currently generates/publishes a coverage CSV and updates the recovery wrapper. Its `scripts/refresh_india_asset_data.py` does **not** persist daily price data for Streamlit. If your India Asset Flow dashboard still reports insufficient history, a separate actual-price snapshot writer/reader integration is needed.
