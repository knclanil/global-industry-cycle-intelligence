# India Asset Flow GitHub Actions publication fix

This fixes the specific `main -> main (fetch first)` rejection after the diagnostics step succeeds. It replaces only `.github/workflows/refresh-india-asset-flow.yml` from the earlier India Asset Flow package. Keep `india_asset_recovery.py`, `scripts/install_india_asset_fix.py`, and `scripts/refresh_india_asset_data.py` already in the repository.

## GitHub Desktop

1. Download and unzip this package.
2. In GitHub Desktop, choose **Repository > Show in Explorer/Finder**.
3. Copy the package's `.github` folder into the repository, merging folders and replacing the existing `.github/workflows/refresh-india-asset-flow.yml`.
4. In GitHub Desktop, **Fetch origin** and **Pull origin** when offered, then commit and **Push origin**. If there is a conflict, resolve it rather than force pushing.
5. In GitHub **Actions**, run **Refresh India Asset Flow Diagnostics** on `main`.
6. Confirm the workflow is green and that `data/dashboard_cache/india_asset_flow_coverage.csv` exists and is nonempty.

## Why the workflow changed

- Checks out the latest `main` with full history.
- Validates that the expected output CSV is present and nonempty.
- Commits generated files only when changed.
- Fetches and rebases onto latest `main` before publishing.
- Retries ordinary push races up to five times, without force-pushing.
- Stops on a true merge/rebase conflict instead of overwriting anyone's changes.
- Serializes runs of this workflow; other workflows can still race, which is why publish retries remain.

This fixes the Git publish failure only. It does not guarantee Yahoo Finance price coverage or that the dashboard is populated. Review the resulting CSV for coverage statuses.
