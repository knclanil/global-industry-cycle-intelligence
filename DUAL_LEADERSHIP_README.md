# USA and Global Company Holdings Leadership

The **Company Holdings Leadership** page has two independent tabs:

- USA Leadership: USA Factor + USA Sector.
- Global Leadership: Global Factor + Global Sector.

Both use 45% factor breadth, 40% relative factor portfolio weight, and 15% sector positioning. Each geographic universe has its own ETF coverage denominator and company rank. Missing sources never imply removals. Portfolio identifiers are internal and not displayed in the tables.

The refresh workflow writes `data/holdings/company_rankings.parquet` for USA and `data/holdings/global_company_rankings.parquet` for Global. It also writes `global_latest_changes.parquet`. A valid refresh is required to populate the Global tab; the Global tab remains visible without the file.

Deploy by copying the contents of `nightly_build/` into the GitHub repository root, committing to `main`, and running **Verified iShares holdings refresh**. Check the workflow for `Saved ... independent Global company rankings`, then reload Streamlit.

Note: Change scores are computed from valid snapshots by the existing ranking engine. Full 30-day decay and multi-day leadership-reversal analytics are not implemented by this change.
