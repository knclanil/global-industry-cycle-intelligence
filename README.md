# USA + India Company Fundamental Data — deployment package

This package is designed to enrich the **existing India and USA Company Deep Dive pages** without changing navigation, the Knowledge Graph, or the verified membership datasets. It **does not contain pre-fetched financial values**; GitHub Actions will retrieve and publish values after installation. Financial provider coverage is not guaranteed.

## Copy into repository (GitHub Desktop)

Extract and merge the `scripts/`, `tests/` and `.github/` directories at the repository root. Replace the existing `scripts/build_usa_research.py` and `.github/workflows/india-financials-refresh.yml` files with the supplied versions; the other files are additions. Do **not** replace `app.py` or any research UI files. Commit and push.

### One-time GitHub secret

In repository GitHub **Settings → Secrets and variables → Actions**, add `SEC_USER_AGENT` with a descriptive value containing a genuine email contact (for example `Research Application contact@example.com`). SEC requests need a valid identifying User-Agent. Do not commit the contact email as source code or share credentials.

### Initial tests (GitHub → Actions)

1. Run **USA Company Fundamentals and Valuations Refresh** with `tickers=AAPL,MSFT`, `limit=2`, `audit_only=false`. These tickers must already be present in your verified USA holdings; otherwise choose two that are.
2. Run **India Company Financials Refresh** with `symbols=RELIANCE,TCS,INFY`, `limit=3`, `audit_only=false`.
3. Inspect action logs and committed `data/usa_research/build_report.json`, `data/usa_research/collection_report.json`, `data/india_financials/kpi_coverage_report.json`, and `data/india_financials/opportunity_build_report.json`.
4. Run both without `tickers/symbols`, default `limit=25` for incremental expansion. The India workflow includes its existing opportunity dataset builder. The USA workflow will generate `data/usa_research/company_research.csv`.
5. Both workflows use a clean detached Git worktree for publishing (no dirty-tree rebase). The USA publication includes `data/fundamentals/`, `data/usa_research/`, and the cross-market coverage report.

### USA collection

SEC CompanyFacts official JSON is downloaded by unique verified ticker ↔ CIK match, cached under `data/fundamentals/facts_<CIK>.json`. Financial metrics from your existing `sec_financials.py` statements include revenue, net income, ROE, operating margin, operating cash flow, FCF, and debt-to-equity when available. Bank financials are treated differently from non-bank financials. Yahoo Finance quotes/ratios are cached separately and accepted only if recent, USD denominated, and ticker-verified. `P/E` and `P/B` are explicitly **provider snapshot values**, not derived from stale annual filings. No valuation or investment composite score is fabricated.

### India collection

Existing Yahoo NSE ticker collection, annual/quarterly statement normalization, atomic cached company snapshots, financial KPI audit, verified NSE-membership join, industry-aware peer calculations and conservative readiness/score gates. Existing Screener.in reference links remain *links*, never scraped.

### Data flow

```
India verified NSE memberships → Yahoo company statements + quotes → summaries
  → opportunity_research.csv → India Screener + India Company Deep Dive

USA verified iShares holdings → SEC companyfacts cache → normalized SEC KPIs
  + dated Yahoo price / P/E / P/B snapshots → company_research.csv
  → USA Screener + USA Company Deep Dive

Both → data/research_coverage/fundamental_coverage.json (metric-by-metric readiness)
```

### Limits and safety

- **No market data is fetched inside Streamlit**; collectors run in GitHub Actions.
- No fake zeros, estimates, imputed facts, or assumed index weights.
- Available financial figures are not necessarily adequate or accurate; check **as-of dates, reporting scopes, currencies and source statements**.
- USA SEC data often covers US-GAAP filers; foreign issuers or nonstandard disclosures may have missing fields.
- India Yahoo statement availability was previously very low; this update does not guarantee improvement or provide a secondary licensed provider.
- Large SEC JSON files can grow repository size. Monitor GitHub data limits and migrate to object storage for sustained high-volume collection.
- USA quality/valuation composite **scores remain blank** pending validated peer, sector, fiscal period alignment. India scoring runs only when its existing data-readiness gates are satisfied.
- GitHub repository **Actions → General → Workflow permissions** must allow read/write to commit data, and branch protection must permit bot commits.

## Validation performed before packaging

Python syntax checks, YAML parsing, 5 isolated USA quote/CIK tests. Full live provider and deployed Streamlit integration **not tested**.
