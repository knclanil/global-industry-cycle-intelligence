# Global Capital Network — direct Global relationships

Replace only `capital_network.py` in the root of your `global-industry-cycle-intelligence` repository.

## Layout

The same five-column plot now contains both paths:

- Country path: **GLOBAL → COUNTRY → SECTOR → COMPANY → FACTOR** (USA / India, when verified)
- Direct global source path: **GLOBAL → global SECTOR → global COMPANY → global FACTOR**, plus distinct direct Global-to-sector, Global-to-company, and Global-to-factor evidence links.

The global data is NOT assigned to any country without evidence. Direct Global links are purple. The three views (Overview, Sector / Factor, Individual Companies), multi-select filters, and company highlighting remain.

## Install with GitHub Desktop

1. Download and extract the ZIP.
2. In GitHub Desktop choose your repository and **Repository → Show in Explorer/Finder**.
3. Copy the ZIP's `capital_network.py` into the repository's main folder; replace the existing copy.
4. In GitHub Desktop: **Commit to main** then **Push origin**.
5. After Streamlit redeploys, open the Capital Network and select the lookback period.

This changes graph rendering and does not regenerate caches. Existing `data/dashboard_cache/rotation_graphs/{global,usa,india}_{1m,3m,6m}_{signals,edges}.csv` must exist for the full network. If datasets are missing, run the Refresh Knowledge Graphs GitHub Action.

Tests: `pytest -q test_capital_network.py` (requires pytest, pandas, plotly; Streamlit needed only for UI runtime). Four targeted tests passed in the build environment. No Streamlit Cloud deployment was performed.

**Important:** These edges represent verified constituent memberships and signal classifications, not measured cross-border capital flows.
