# India Asset Flow — clean GitHub Actions publish fix

This replaces `.github/workflows/refresh-india-asset-flow.yml`.

The former workflow called `scripts/install_india_asset_fix.py`, which **modifies** `india_asset_market_data.py` in its checkout, then committed only some generated files and ran `git rebase`. Git refused to rebase a dirty working tree.

The replacement publishes only `data/dashboard_cache/india_asset_flow_coverage.csv` from a **separate clean Git worktree**. If the remote branch advances, it fetches the latest version, resets the isolated worktree, copies the generated CSV, and retries without force-pushing.

## Install with GitHub Desktop

1. Fetch/Pull origin in GitHub Desktop.
2. Unzip this package; copy `.github/workflows/refresh-india-asset-flow.yml` into the same path in the local repository, replacing the old workflow.
3. Commit and push using GitHub Desktop.
4. On GitHub select Actions > Refresh India Asset Flow Diagnostics > Run workflow (main).
5. Open `data/dashboard_cache/india_asset_flow_coverage.csv` to verify successful publication.

## Limitations

This workflow publishes a *coverage diagnostics CSV*, not actual historical price files. It does **not** solve a Streamlit dashboard that reads missing price snapshots. Also the recovery wrapper is installed only within the temporary GitHub Actions runner, not permanently into the deployed application. A separate price-snapshot publishing workflow is required for an offline dashboard.
