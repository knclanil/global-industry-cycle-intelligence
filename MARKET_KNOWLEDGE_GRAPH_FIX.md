# Global, USA & India market-rotation knowledge graphs

## What was broken

The previous regional graphs used `data/dashboard_cache/*_companies.csv`, which were empty for both Global and USA in the supplied snapshot (`manifest.json` records 0 companies and 0 source ETFs for each). The old visual was also a high-membership holdings graph: it never read market-rotation signals and therefore could not identify leading or lagging companies.

## New behavior

The region-specific graphs now use **materialized, source-evidenced leading and lagging company results** calculated from saved ETF/index market histories and holdings. Each is a distinct 2D graph. Sector sources are on the left, companies in the middle, factor sources on the right. The dashboard does not recalculate the market signals or download data during viewing.

- Scope: Global / USA / India, independently.
- Windows: 1, 3, 6 months.
- Leading: both a verified leading sector source and a verified leading factor source.
- Lagging: both a verified lagging sector source and a verified lagging factor source.
- Ranking: retained existing `leading_lagging_engine.build_lists` *evidence score* methodology. No ranking V2 substitution.
- USA/Global source links can be **clearly labeled category ETF price proxies** where the exact holdings ETF's price series is not mapped.
- The graph DOES NOT establish individual company price momentum. Avoid claims that company stock prices are rising/falling solely from index membership.
- `Avg ETF % weight` is carried through where verified.

## Operation

1. Refresh price histories with the repository's market refresh workflow.
2. Refresh verified iShares and NSE holdings with existing holdings workflows.
3. Run **Build dashboard database snapshots** (manual or scheduled). This now also calls `scripts/build_regional_rotation_graphs.py`.
4. GitHub commits `data/dashboard_cache/rotation_graphs/*` including CSVs and a coverage manifest.
5. Reboot/reload Streamlit and open **Knowledge Graphs → Global / USA / India**.

Diagnostics for empty regions are available under **Data coverage**, including verified signal counts, unmatched sources, and any build error.

## Important maintenance

`pyarrow` is required for the source parquet files. The cache materializer now fails explicitly when it cannot read a *present* parquet snapshot, rather than silently overwriting the materialized Global and USA views with empty CSVs. Do not run the builder without its requirements. On first deployment, the Global and USA rotation graphs will remain unavailable until the scheduled builder runs successfully, even if the code update is deployed.
