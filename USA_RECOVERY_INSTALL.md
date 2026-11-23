# USA consolidated KPI recovery update

Install by extracting this ZIP into the root of the existing `global-industry-cycle-intelligence` repository, preserving paths. Commit and push with GitHub Desktop. Then run **USA Company Fundamentals, Quotes and Ranking Refresh** in GitHub Actions. Use `sec_limit=0` only if you want to refresh missing/stale SEC records; existing SEC caches are reused. Quote collection remains independently limited.

## Changes
- Reuses SEC CompanyFacts (no StockAnalysis/Finviz bulk scraping).
- Reads comparative annual facts by observation end year rather than SEC filing FY label; supports basic EPS when diluted is unavailable, and uses an absolute previous-year denominator for earnings turnaround growth.
- Requires matching EPS concept for year-over-year comparisons, rejects zero EPS baselines, aligns all reported financial inputs to the same annual period within 45 days.
- Emits `data/usa_research/fundamental_kpi_gap_audit.csv` with every verified issuer, missing-field flags, ranking status, and manual verification links.
- Adds a dedicated recovery test step to the existing GitHub Actions workflow; preserves the dashboard and other workflow stages.

## Caveats
- Tests run locally on fixtures, **not** the live SEC universe. Actual additional ranking coverage is unknown until GitHub Actions finishes and publishes its reports.
- Companies lacking comparable filings, or ineligible financial firms, remain unranked. Finviz and StockAnalysis are manual verification links only.
- This update does not replace quote providers or claim complete market-cap coverage.
