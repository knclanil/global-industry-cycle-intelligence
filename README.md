# Automatic Yahoo Finance sectors for all discovered companies

This is an **add-on**, not a replacement for your app or existing ETF taxonomy.

## Install using GitHub Desktop

1. Copy `scripts/refresh_company_sectors.py` into your repository's `scripts` folder.
2. Copy `.github/workflows/refresh-company-sectors.yml` into `.github/workflows` in the repository.
3. Commit and Push in GitHub Desktop.
4. In GitHub: **Actions → Refresh Company Sectors (Yahoo Finance) → Run workflow**.
5. After success, look for `data/dashboard_cache/company_sectors/company_sector_mapping.csv` and `summary.json`.

The script discovers unique underlying company ticker symbols from:

- `data/holdings/latest_holdings.parquet` (`ticker`)
- `data/india_holdings/constituents.csv` (`symbol`, normalized to `.NS` where appropriate)
- `data/dashboard_cache/rotation_graphs/*_edges.csv` (`Ticker`)

The union is fetched, deduplicated, with retries, progress checkpointing, and a 7-day cache.
Most Yahoo company sectors are in English (e.g. `Technology`, `Financial Services`).
`quoteType=ETF` is **not** treated as a sector. Existing ETF/index taxonomy still determines
categories such as Small Cap or Communications.

## Key limitations

- No Yahoo lookups have been executed in this development environment (external network is unavailable).
- This generates a **lookup CSV** only. It does **not** yet overwrite company-sector edges or
  make unverified ETF constituent memberships. Yahoo sector mapping can be incorporated later
  as a *separate, provenance-labeled classification edge*.
- Yahoo may throttle or block bulk requests. Increase `--delay` or run in smaller batches if needed.
- `.NS` normalization assumes India constituent `symbol` values are NSE-listed stocks. Verify
  that symbols are not already internationally suffixed or index identifiers.
- The stock universe is the union of **available cached holdings and graph edges**. It is not
  automatically every publicly listed company in all 20 countries.
- If your repository uses large git-tracked snapshots, changes may be substantial.
