# Assets → Sectors → Factors + matching verified company memberships

## Installation with GitHub Desktop

1. Open GitHub Desktop and choose `global-industry-cycle-intelligence`.
2. Use **Repository → Show in Explorer/Finder**.
3. Copy **app.py** and **regional_rotation_graph.py** from this package to the repository root (beside the existing app.py), replacing the old copies. **Do not copy build_patch.py**.
4. Commit `Reorder market pages and sync graph membership filters`, then **Push origin**.
5. Streamlit Cloud should redeploy automatically. No data cache regeneration is needed for this presentation/filtering-only change.

## Changes

- Reorders Global, USA and India navigation so **Asset Flow → Sector → Factors** occur in that sequence (Global Countries remains first).
- Changes the **Verified company memberships** table on the knowledge graph page to use **the identical filters and evidence graph node selection** as the graph above it.
- Supports the existing multi-select controls: rotations, sector sources, factor families and companies, plus ANY / ALL matching and lookback.
- Enforces rotation selection consistently: unrelated source nodes and their rows do not appear merely because a company is also in another quadrant.
- Every membership row still retains its original index source, company key, rotation and evidence. It does **not** merge away raw source-level data.
- The graph may cap displayed company dots to 60/100 for speed; the filtered membership table displays **all matching membership rows** and has CSV export. It may therefore contain more companies than are rendered as dots.
- Changes are shared by **Global / USA / India** knowledge graph pages.

## Caveats

This table is driven by `data/dashboard_cache/rotation_graphs/{region}_{period}_edges.csv`, exactly as the graph. It is **not** the separate summary table at `data/dashboard_cache/{region}_companies.csv`. If an index has no valid rotation signal and no eligible membership edge, neither the graph nor this table can display it as a mapped index without an upstream data update.

## Validation

Python syntax checks and five targeted unit tests passed using fixture nodes, signals and edges. The update is not yet verified in the live Streamlit deployment. Run `python -m unittest discover -s tests -v` from the repository root to test against the repository's `rotation_graph_evidence.py` module.
