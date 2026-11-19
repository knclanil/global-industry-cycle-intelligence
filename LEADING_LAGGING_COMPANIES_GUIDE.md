# Leading & Lagging Companies · Sector × Factor

This is a **separate 2D knowledge graph** alongside the existing Capital Network. The page has three strictly independent markets: **Global, USA and India**. For each, it shows two independent ranked lists and corresponding graphs: **Leading companies** and **Lagging companies**.

## Signal definition (source-market-relative, not stock returns)

For a source index/ETF, use stored, validated adjusted-close series alongside its own benchmark:

- RS = 100 × [(source/benchmark at last observation) ÷ (source/benchmark L trading sessions earlier) − 1].
- RS momentum = current RS − RS observed approximately L/2 trading sessions earlier (same L-length RS calculation).
- **Leading**: RS >= 0 and RS momentum >= 0.
- **Lagging**: RS < 0 and RS momentum < 0.
- **Improving** or **Weakening**: not put into either list, rather than treating them as leading/lagging.

Company inclusion requires **one verified sector source AND one verified factor source in the SAME category**. A company can appear on both lists only if independent sector/factor source sets justify each classification. Unknown price or holdings data never becomes a negative observation. "Lagging" does NOT mean a cheap stock or bargain, and "Leading" does NOT mean that the company's share price has positive momentum.

## Rankings

For each company, compute the mean of `abs(RS) + 0.5 * abs(RS momentum)` separately over its matched sector and factor sources. The final evidence score = geometric mean of those two values + a small capped breadth tie-breaker. Scores are **ordinal research indices only** and are NOT normalized to 100 or compared between markets/lookbacks. Equal-score ties use competition ranking. The opposite sign of RS determines Leading vs Lagging, not a different formula. For USA/Global, weights remain separate verified raw ETF allocations; for India, constituent memberships remain unweighted. No source index is counted twice for the same company.

## Data prerequisites

Run the existing `nightly-market-refresh` GitHub Actions workflow so the app can read `data/market/<market>/<ticker>.parquet`. Existing holdings refresh workflows must have saved:

- Global / USA: `data/holdings/latest_holdings.parquet`
- India: `data/india_holdings/constituents.csv`

For India, exact canonical NSE index-to-market-ticker matches are defined in `leading_lagging_engine.py` and only available matches are used. Some thematic/factor indices have no corresponding saved rotation index. Those are correctly **unmapped**.

For Global/USA, the price-history ETF tickers in the sector/factor analysis are **not automatically assumed to be the same fund as a source holdings portfolio**. Create a **verified mapping** at `data/market/rotation_source_links.csv`:

```csv
region,source_id,market_ticker,kind
USA,ACTUAL_PORTFOLIO_ID,VERIFIED_PRICE_TICKER,sector
GLOBAL,ACTUAL_PORTFOLIO_ID,VERIFIED_PRICE_TICKER,factor
```

Only map a portfolio ID when the price series is the same actual ETF / a deliberately documented and methodology-appropriate proxy. To avoid giving a proxy a false identity, if using a proxy, document the relationship and avoid labeling the result as that ETF's own performance. Valid market keys: `USA` / `GLOBAL`; valid `kind`: `sector` or `factor`. The UI displays missing coverage clearly. **Do not fill mappings by guessing.**

No new live API requests run when opening the page; it reads saved files. Restart or refresh the app when background data is committed.

## Deployment

Copy all `nightly_build/` *contents* into your repository root. Preserve existing `data/` holdings, financials, historical snapshots, caches, and GitHub Actions permissions. This is a build package, **not a live GitHub deployment**. A runtime visual acceptance test has not yet been performed in Streamlit Cloud.

## USA / Global blank-page fix — November 19, 2026

Previously `data/market/rotation_source_links.csv` was header-only. Consequently, all
USA and Global sources were unmapped, despite having valid source holdings.

The engine now **automatically identifies an unambiguous sector/factor category
from the fund title supplied in each iShares holdings download**, and uses the
existing market-history **reference ETF for that category**. Each result is
labeled **Category ETF proxy**, not a direct return or price history of the
source holdings fund. Exact operator-verified mappings in
`data/market/rotation_source_links.csv` still override the fallback.

No company is classified if its sector or factor price-history signal is absent,
if its fund's category is ambiguous, or if the sector and factor signals don't
agree on Leading or Lagging. Missing signals are never treated as lagging.

**To populate**: Run both the Verified iShares holdings refresh and the
Incremental market data refresh (`region=us` or `all`). Check that
`data/holdings/latest_holdings.parquet` contains `fund_title` and that
`data/market/` contains valid adjusted-close histories. Open
Leading & Lagging → Global / USA → Rotation & coverage for uncovered funds.

A proxy is a research benchmark and not proof that its holdings fund is
outperforming. For exact source-fund returns, supply a verified portfolio-ID
→ traded-ticker map and save the traded ETF's own price series.
