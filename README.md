# USA verified-ticker financial coverage — full pipeline

This package updates the existing USA collection, reconstruction, ranking and reporting pipeline. It **does not contain collected live SEC or Yahoo data**. Live data is fetched by GitHub Actions after you commit/push this package.

## Install
Copy the `.github`, `scripts`, and `tests` folders into the root of your existing GitHub Desktop repository (merge and replace matching files). Commit and push. No installer is needed. Do not replace app.py or the Knowledge Graph.

Run **Actions → USA Company Fundamentals, Quotes and Ranking Refresh → Run workflow** on `main` with SEC limit 250 and quotes limit 250. The workflow also runs on weekdays. Set GitHub Actions secret `SEC_USER_AGENT` with a real contact email. The first run will NOT cover all ~2,921 tickers; new/stale data is collected in successive runs, and coverage depends on source availability. Avoid concurrent duplicate runs. Each run is bounded to avoid provider overload and GitHub Actions timeouts. Existing cached data is retained.

## Published outputs
- `data/usa_research/all_ticker_financial_coverage.csv` — every verified company record, its ticker, available KPI count, missing fields, SEC/quote status and rank.
- `data/usa_research/all_ticker_financial_coverage.json` — full-universe progress counters and unmapped ticker list.
- `data/usa_research/fundamental_rankings.csv` — values and ranks for the full verified issuer universe; missing metrics remain blank/unranked.
- `data/usa_research/fundamental_field_evidence.csv` — SEC concept and filing evidence.
- `data/usa_research/collection_report.json`, `quote_pilot_report.json`, `fundamental_ranking_report.json` — diagnostics.

## Important limitations
- The SEC official CompanyFacts API is the primary source for U.S. listed issuers; not all companies have comparable US-GAAP tags or SEC CompanyFacts.
- Yahoo via `yfinance` is an unofficial supplementary market data feed; quote failures, symbol mismatches, and rate limiting are possible.
- Financial-sector companies may not be eligible for the general five-KPI ranking.
- Market capitalization breaks ties ONLY; it does not increase fundamental scores.
- No StockAnalysis/Finviz scraping and no Alpha Vantage.
- This package was tested offline (12 tests and syntax/YAML parse); no live provider requests or deployed GitHub Actions runs were performed here.
