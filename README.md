# One-row-per-company membership table

This replaces **only** the *All verified company memberships* table display in `regional_rotation_graph.py`. It preserves Knowledge Graph rendering, its controls, matching cohorts, and the independent company-table filter modes.

The table shows the columns, in order:

**Company | Ticker | Quadrant | Sector | Factor | Mapping | Weight | Avg Weight**

Each `company_key` produces one row. Multiple distinct quadrant/sector/factor/mapping values are joined into a single cell using ` · `; factor source indexes are normalized into factor families (Value, Quality, etc.). Company identities are **not** collapsed merely because their names or tickers look similar. The underlying index/ETF membership evidence remains available in an expandable source-level table and as a CSV download.

**Weight** is a list of recorded per-source holding weights (one per distinct source/portfolio membership with a usable weight), not their sum. **Avg Weight** is the arithmetic mean of those reported weights, excluding missing values; it is not the weighted-average portfolio exposure or a recommended investment allocation. India source snapshots without constituent weights show `N/A` for Weight and an empty Avg Weight.

## Install through GitHub Desktop

1. Extract this ZIP.
2. In GitHub Desktop select `global-industry-cycle-intelligence` → Repository → Show in Explorer.
3. Copy `regional_rotation_graph.py` into the root of the repository, alongside `app.py`, replacing the existing file.
4. Commit (`Show company memberships one row per company`) and Push origin.
5. Open Global, USA, or India Knowledge Graph, expand *All verified company memberships*, and select your preferred table source.

No cache regeneration is required. If your local `regional_rotation_graph.py` has newer custom changes, review the diff before replacing it.

## Validation

Syntax compilation passed; two isolated aggregation tests passed. Full Streamlit deployment has **not** been tested. This file is based on the last graph/table sync package provided in the conversation.
