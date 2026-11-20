# Map country rotations in the Capital Network

This is an add-on to your existing GitHub Desktop deployment. Copy these files into the repository keeping their folder paths:

- `capital_network.py`
- `scripts/build_country_rotation_snapshots.py`
- `.github/workflows/refresh-country-rotations.yml`

The graph creates a country node for each of the 20 tracked ETFs and connects the country to its own country-level rotation (Leading, Improving, Weakening, Lagging), based on relative strength versus ACWI. Unavailable observations connect to **Unclassified (missing data)**, rather than being assigned a fake category.

The workflow can be run at GitHub > Actions > Refresh Country Rotations > Run workflow, and it also runs on weekdays. Verify its run is green and its output CSVs committed to main:

- `data/dashboard_cache/rotation_graphs/country_1m_rotations.csv`
- `data/dashboard_cache/rotation_graphs/country_3m_rotations.csv`
- `data/dashboard_cache/rotation_graphs/country_6m_rotations.csv`

The graph uses the selected lookback to map `Global → Rotation → Country`. All tracked countries appear unfiltered in Overview; active filters intentionally hide unrelated countries. Only USA and India have country-scoped sector/company memberships from the existing graph sources, so other countries can be correctly connected to their rotation while their sector/company branches remain empty.

The separate `GLOBAL → global-scoped sectors/companies/factors` branch is preserved. Other Graph pages are not changed. A fully populated country-to-company network would require new, verified constituent datasets for the additional countries.

If workflow fails, read its logs; don't assume classifications were produced.
