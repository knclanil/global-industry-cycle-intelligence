# India Nifty unmapped-source expansion

This package adds the 13 requested India constituent indexes to the knowledge graph *when valid, independently retrieved index price histories are available*.

## Files to copy (GitHub Desktop)

1. `india_index_rotation_expansion.py` → repository root, alongside `app.py`.
2. `scripts/build_regional_rotation_graphs.py` → replace the matching file in the repository's `scripts` folder.
3. `tests/test_india_index_rotation_expansion.py` → optional tests.

Commit and push using GitHub Desktop. Then rerun **Refresh Knowledge Graphs** in GitHub Actions, after the India holdings refresh. It should run the updated `scripts/build_regional_rotation_graphs.py` in the repository root.

## What this does

- Registers three sectors: Nifty Oil & Gas, Nifty India Defence, Nifty India Manufacturing.
- Registers ten factor indexes and their correct factor families (Value, Momentum, Quality, Alpha, Low Volatility, Growth, Dividend).
- Fetches official NSE-index histories from the existing repository NSE readers when they work. No unofficial Yahoo ticker is invented.
- Calculates verified 1M/3M/6M quadrant signals against the stored Nifty 50 benchmark, using the repository's relative-strength/momentum formula.
- Augments `_signals.csv`, generates verified membership `_edges.csv`, and rebuilds `_unmapped.csv`.
- Writes `data/dashboard_cache/rotation_graphs/india_extra_index_history_status.csv` to explain *every missing index*, including network/provider failures, stale histories and insufficient dates.

## Important limitation

Classification (factor vs sector) is **not** the same as a rotation signal. NSE sometimes restricts automated history; if there is no usable price series, the record remains unmapped with an honest reason. Company memberships are not invented.

## Check results

After the workflow finishes, review:

- `data/dashboard_cache/rotation_graphs/india_extra_index_history_status.csv`
- `data/dashboard_cache/rotation_graphs/india_3m_signals.csv`
- `data/dashboard_cache/rotation_graphs/india_3m_edges.csv`
- `data/dashboard_cache/rotation_graphs/india_3m_unmapped.csv`

If all 13 have `status=unavailable`, investigate NSE API/network access or supply validated historical index closes in your existing market-history store. Do **not** force them into a rotation bucket without price history.
