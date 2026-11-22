# USA all-ticker SEC backfill — based on uploaded repository (2026-11-22)

This patch contains ONE full replacement workflow: `.github/workflows/usa-company-fundamentals-refresh.yml`.

## Verified findings from uploaded source and data
- 2,931 verified company records / 2,921 unique tickers.
- 2,899 mapped SEC ticker identifiers; 882 CompanyFacts cached at snapshot time.
- 364 fully ranked; 2,567 unranked.
- Previous workflow defaulted to 125 SEC downloads and 125 Yahoo quote attempts per run despite dispatch form showing 250.
- This workflow sets SEC `--limit 0` to fetch **all missing** SEC CompanyFacts in one run, while keeping previously cached records (stale-days 3650). Requests are rate paced and retry on transient errors.
- Yahoo quote requests are bounded at 300 per run by default, because attempting ~2,900 Yahoo quote requests in one job can trigger throttling; rerun or rely on weekday schedule to expand quote coverage.
- Financial companies and companies with incomplete/incomparable filings remain unranked by design. This patch does not fabricate their financial values.

## Install
Copy `.github/workflows/usa-company-fundamentals-refresh.yml` into the repository at the same path; commit and push. Run **a NEW** GitHub Actions execution on `main` named `USA Company Fundamentals, Quotes and Ranking Refresh`. Leave `sec_limit=0` and `quotes_limit=300`.

## Confirm
After run, inspect `data/usa_research/collection_report.json`, `all_ticker_financial_coverage.json`, `fundamental_ranking_report.json`, and `fundamental_rankings.csv`. SEC failures or Yahoo throttling may require reruns. The live run is not executed by this package.

## Scope
No dashboard navigation, knowledge graph, India code, or ranking formula changes. Workflow uses existing repository scripts as inspected from the uploaded ZIP.
