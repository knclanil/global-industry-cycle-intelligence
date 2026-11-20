# Global Capital Network: one canonical relationship table

Replace **only `capital_network.py`** at the repository root using GitHub Desktop, then **Commit to main → Push origin**. The existing cache builder and GitHub Actions workflows stay in place. This implementation reads existing `country_{period}_rotations.csv` plus `{region}_{period}_signals.csv` and `{region}_{period}_edges.csv` at runtime (for 1m/3m/6m), so no new snapshot or workflow is required.

## What's different

- Builds **one canonical backend DataFrame** with six main columns: **Global, Rotation, Country, Sector, Company, Factor**, plus unique source IDs, signal quadrants and evidence coverage.
- Constructs visualization edges **only from adjacent columns**. No long Global → sector or Global → company lines bypassing columns.
- Displays the Global-direct data in a clearly named **Global scope** rotation and **Global direct** scope (not a country or a calculated market rotation), so all visible paths follow the same six-column structure.
- Each country links to its actual country ETF rotation when that data is available.
- Country → Sector → Company links require actual country-scoped membership data. **USA and India currently have those caches**; the other 18 country nodes remain country-only until you collect their verified constituents. The graph will never invent downstream connections.
- A factor-only membership does not justify inventing a sector link. Those entities may be disconnected from an upstream country chain: this is a real data gap, explained by the canonical table's `coverage` field.
- Multiple rotation, country, sector, company and factor selections; unrelated countries and company records are removed on filter. Company-centric detail remains available in the backing table. Full data can be downloaded via the Streamlit page's CSV button.
- Default number of company nodes is limited for readability; **Show all matching companies** expands them.

## Expected cached inputs

`data/dashboard_cache/rotation_graphs/`:

- `country_1m_rotations.csv` (and 3m, 6m), with `ETF`, `Quadrant`
- `usa_1m_signals.csv`, `usa_1m_edges.csv` (and 3m, 6m)
- `india_1m_signals.csv`, `india_1m_edges.csv` (and 3m, 6m)
- `global_1m_signals.csv`, `global_1m_edges.csv` (and 3m, 6m)

If cache files are absent, the app exposes diagnostics and does not fabricate relationships.

## Run tests

After `pip install -r requirements.txt` and `pip install pytest`:

`python -m pytest tests/test_capital_table.py -q`

These tests use minimal temporary CSVs. Deployment in your live Streamlit Cloud environment still needs verification.
