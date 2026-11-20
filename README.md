# Complete four-quadrant knowledge graphs — Global / USA / India

The chart is ONE connected three-column view:

**Leading, Improving, Weakening, Lagging → ALL available sector/factor signals → ALL verified companies**.

Unlike the prior graph, this module does not use the filtered `*_companies.csv` research ranking to decide graph connectivity. It exports `*_edges.csv` directly from holdings/index memberships and verified source mappings. Sector-only and factor-only memberships are included. Sectors/factors with valid signals but no verified company membership still render.

## Installation

Copy these files into your repository:

- `regional_rotation_graph.py` → repository root (replace existing)
- `rotation_graph_evidence.py` → repository root (new)
- `build_regional_rotation_graphs.py` → `scripts/build_regional_rotation_graphs.py` (replace existing)

No changes to `leading_lagging_engine.py` are required. Existing strict screening logic remains unchanged for Leading/Lagging research screens.

After refreshing market price histories and holdings/index constituent data, run:

```bash
python scripts/build_regional_rotation_graphs.py
```

The builder generates `data/dashboard_cache/rotation_graphs/{global,usa,india}_{1m,3m,6m}_{signals,edges,companies,unmapped}.csv` and `manifest.json`. Ensure the application deployment can see these refreshed cache files, either by committing them where appropriate or regenerating during your deployment/data job. A Streamlit reboot alone does not create missing snapshots.

Start the app as usual: `streamlit run app.py`. The existing `render_graph(region)` function remains the public entry point.

## Reliability and caveats

- Membership is mapped using the existing verified exact mapping or declared category-proxy methodology from `leading_lagging_engine.py`. A category proxy is *not* identity of underlying price series.
- Index-level rotation labels must NOT be interpreted as individual company stock-price signals.
- Missing/invalid price histories, unmatched fund names, companies without verified IDs, or invalid holding weights cannot be fabricated into connections.
- Some rotations may have zero qualifying market signals; they remain visible and coverage warnings explain why.
- All companies and links are retained by default. For very large inventories the browser may be slow; the plot is scrollable, zoomable and pannable, with the underlying complete membership table available.
- Names of identical company IDs are deduplicated across different source memberships. A company can have edges into multiple quadrants.

## Check

```bash
python -m pytest tests/test_complete_rotation_graph.py -q
```
