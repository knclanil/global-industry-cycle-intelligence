# USA financial recovery follow-up — install

Copy all files from this ZIP into the ROOT of your GitHub repository, preserving directories, then commit and push. Run **USA Company Fundamentals, Quotes and Ranking Refresh** with `sec_limit=0` and `quotes_limit=500` (or 250 if provider throttling occurs).

## Fixes
- Official SEC ticker lookup now normalizes share-class spaces, dots and hyphens (no guessed CIK).
- Yahoo share-class requests normalize spaces to hyphens, while stored ticker identity remains unchanged.
- Financial institutions are explicitly classified as ineligible even when metrics are missing.
- Missing KPI names are included in per-company ranking reasons.
- `fundamental_kpi_gap_audit.csv` no longer gets overwritten by a reduced-column status table; the separate status output is `fundamental_kpi_status.csv`.
- Regression tests run in GitHub Actions.

## Limits
This is a targeted, tested follow-up, **not** a guarantee of five KPIs for all 2,931 issuers. Source financial statements can lack comparable data; the run must publish a new ranking report before any increase can be claimed. `SEC` source tags are still required for official fundamental values.

## Verify
After Actions succeeds, check `data/usa_research/fundamental_ranking_report.json`, `fundamental_kpi_gap_audit.csv`, and `fundamental_kpi_status.csv`. The workflow does not need to re-download the entire SEC cache.
