# Regional intelligence: data pipeline and navigation

## Navigation

- Knowledge Graphs → Global / USA / India; the existing Global Capital Network and Leading/Lagging pages remain as separate advanced views.
- Global → Sector / Factor / Sector–Factor–Holdings Analysis.
- USA → Sector / Factor / Sector–Factor–Holdings Analysis.
- India → Sector / Factor / Sector–Factor–Holdings Analysis, with existing NSE index browser and overlap tools.
- Company Financials → existing USA and India research, quality, and valuation pages.
- Other Research → asset/country views, holdings leadership and documentation.

## Observed source coverage in the supplied repository snapshot

- NSE: 31 index CSV datasets, 328 distinct securities, 975 memberships, no reported weights.
- iShares holdings coverage metadata: 32 verified of 33 expected ETFs; the stored holdings are in `data/holdings/latest_holdings.parquet`.
- India financial summary contains 25 company records but zero non-null revenue values; background statement coverage is incomplete.
- SEC refresh reports 500 cached company-facts documents (the documents are stored separately), which do **not** imply 500 fully validated histories.
- Market prices are stored in `data/market/{market}/*.parquet` with incremental market refresh for India and US/global instrument groups.

## Collection and materialization

1. `.github/workflows/nightly-market-refresh.yml`: daily market-price histories (exchange-local trading days).
2. `.github/workflows/holdings-refresh.yml`: verified iShares constituents (holdings are **not** daily unless their issuer updates them).
3. `.github/workflows/india-constituents-refresh.yml`: NSE constituent snapshots and historical membership events.
4. `.github/workflows/fundamentals-refresh.yml`: SEC company facts, incremental batches, identification required.
5. `.github/workflows/india-financials-refresh.yml`: Yahoo data where legally and technically available; the provider may return incomplete statements.
6. `.github/workflows/build-dashboard-cache.yml`: **offline** derived, dashboard-ready CSV files and manifest after the other collectors.

The cache build requires dependencies in `requirements.txt`, including `pyarrow` for iShares/market parquet files. Run `python scripts/build_dashboard_cache.py` locally or through the workflow. `--include-sec` optionally runs the existing multiyear ranking engine offline; it may take substantially longer.

## Data contract

`data/dashboard_cache/` contains region-scoped materialized files:

- `{global,usa,india}_companies.csv`: company identities, source index memberships and available company KPI snapshot columns.
- `{global,usa,india}_indices.csv`: source index descriptions, counts and observation dates.
- `{global,usa,india}_sector_factor_matrix.csv`: exact unique-security intersections where supplied.
- `manifest.json`: data completeness and build time.
- `{region}_fundamental_quality.csv`: only if optional historical materialization was explicitly run and had usable data.

There is **no synthetic imputation**. A missing number is unknown, not zero. Financial coverage counts are measured from non-null values. Market prices, index composition, financial reporting periods and model-update dates are not interchangeable. Global non-SEC issuers need a separate authorized filing provider for complete fundamental coverage.

The new Streamlit regional pages only read these materialized CSV snapshots and never initiate a provider request. The independent legacy financial research pages retain their existing on-demand behavior.

## Recommended daily order

1. Market data and holdings/constituent refresh when appropriate.
2. SEC / India company financial ingestion and validation.
3. Rebuild materialized views after collectors have completed. Scheduling is an operational convenience, not a guarantee that the collectors finish before materialization; manually dispatch the build after refreshing its inputs when a synchronized snapshot is required.
4. The Streamlit page reads a few indexed CSV files and renders without re-parsing raw SEC facts.

## Limits

- ETF holdings cannot truthfully be described as **daily** when issuer updates are less frequent.
- Indian constituent weights are unknown until verified NSE factsheets/weight files are integrated.
- Financial data licensing, source accessibility and company statement basis (consolidated versus standalone) need validation before commercial redistribution.
- Graphs are a selected 2D membership visualization for readability; complete data is available in tables/exports.
