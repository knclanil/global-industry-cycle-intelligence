# India Company Financial KPIs — On-demand Yahoo + full universe refresh

## What changed

**Company research is no longer restricted to 25 companies.** The India Company Financial KPIs page supports **direct NSE ticker search** even when the company is absent from the 31 index constituent lists. Yahoo Finance is used for on-demand annual and quarterly income, balance-sheet and cash-flow statements and quoted market data when available. Enter `MGL` or `MGL.NS` and click **Fetch live Yahoo financials**. The first request can be slow or fail with HTTP 429 depending on Yahoo access from Streamlit Cloud. The page itself does not make network requests until that button is clicked.

When a cached snapshot already exists, the app displays it immediately. A successful live request overrides the cached snapshot for this Streamlit session (15-minute function cache). It **does not automatically commit it to GitHub**. The background workflow writes persistent JSON and summary CSVs.

### Provider links for MGL

- [Yahoo income](https://finance.yahoo.com/quote/MGL.NS/financials/)
- [Yahoo balance](https://finance.yahoo.com/quote/MGL.NS/balance-sheet/)
- [Yahoo cash flow](https://finance.yahoo.com/quote/MGL.NS/cash-flow/)
- [Screener consolidated report](https://www.screener.in/company/MGL/consolidated/)

### Background refresh: every index company

The **India Company Financials Refresh** GitHub Action now defaults to `limit = 0` meaning *all eligible NSE companies*, not 25. GitHub Actions can take a long time for hundreds of tickers; it checkpoints the provider results every 20 attempts and commits on completion or when the 160-minute collection budget is reached. Yahoo service limits and missing statements may reduce actual coverage. The next run can continue because files already refreshed within `--stale-days` are skipped. To refresh ALL cached entries irrespective of staleness, use `--force` in the CLI (not recommended frequently).

```bash
python scripts/refresh_india_financials.py --limit 0
python scripts/refresh_india_financials.py --symbols MGL --limit 0
python scripts/refresh_india_financials.py --rebuild-only
```

`--symbols MGL` is valid even if MGL is not in the saved index universe; its record is tagged `TICKER:MGL` and **does not create NSE membership**. Missing figures remain N/A. NSE provides verified membership data, not the three financial statements. Yahoo statements can differ in consolidation scope from Screener; source periods, retrieval timestamps and financial currencies are shown.

### Screener usage and rights

The app links to Screener consolidated financials for independent research but **does not automatically scrape or republish Screener's HTML**. Screener's published terms limit reuse and public display of site materials, and Yahoo Finance API data is described by `yfinance` as for personal research use. Obtain appropriate data rights for public/commercial dissemination. Both sources can rate-limit or block cloud requests. If Yahoo denies access, the existing cached snapshot remains visible and the app offers the exact Screener/Yahoo source links.

### Deployment

Extract `nightly_build/` contents to the repository root; do not overwrite existing `data/india_holdings` or `data/india_financials` snapshots. Commit and push; let Streamlit redeploy. The financials refresh action can be run manually for the entire universe (input `limit=0`) or a single ticker. The page has not been live-tested against Yahoo from Streamlit Cloud in this environment.
