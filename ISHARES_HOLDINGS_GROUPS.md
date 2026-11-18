# iShares holdings: fund-title grouping

Each holdings document's first-column fund title is captured verbatim as `fund_title`.

The holdings interface displays three named groups: **USA Factor**, **USA Sector**, and **Global Sector**. Fund titles, rather than portfolio identifiers, are used as the visible names in group tables and company exposure drill-downs.

Group membership is mapped to the supplied BlackRock source inventory; fund titles are preserved as issuer-provided and are not guessed from ticker symbols. The 10 previously pending Global Sector sources are ingested and stored in `latest_holdings.parquet` alongside the USA sources. Their holdings are visible under Global Sector, but they do not automatically alter the established USA leadership score.

**Deployment:** Replace the project files and run the verified holdings refresh. Existing stored Parquet snapshots may lack the new `group` and `fund_title` fields; the next successful refresh writes them. Existing dashboard pages are retained.
