# USA Company Financials + Fundamental Ranking — installation package

**Scope:** USA only. Retains all existing USA/India pages, graphs, holdings, Financial Research, Financial KPIs, and the opportunity screener. This package does **not** scrape StockAnalysis or Finviz and requires no Alpha Vantage or FMP key.

## What this ZIP contains

- `scripts/refresh_usa_company_fundamentals.py`: SEC CompanyFacts incremental collection for the verified USA issuer universe.
- `scripts/usa_quote_coverage_pilot.py`: Yahoo quote and market cap collection; invalid ticker protection, prioritizes fundamental-ready issuers, prioritizes never-collected quotes, and uses a 40-day quote refresh window to prevent forever refreshing the first symbols.
- `scripts/usa_sec_cache_reader.py`: read cached SEC facts by verified SEC CIK.
- `scripts/build_usa_research.py`, `scripts/usa_financial_gap_report.py`, `scripts/unified_fundamental_coverage.py`: reconstruct and audit existing USA research datasets.
- `scripts/build_usa_fundamental_rankings.py`: extract annual SEC facts, calculate five ratios including EPS **YoY percentage growth**, assign ranks and emit source evidence.
- `.github/workflows/usa-company-fundamentals-refresh.yml`: existing USA automated workflow *replacement*, with collection, quote enrichment, dataset build, ranking build, validation, and clean-worktree GitHub publishing.
- `usa_fundamental_rankings_ui.py`: standalone Streamlit ranking component; placed inside existing USA Financial KPIs.
- `scripts/install_usa_rankings_in_kpis.py` and `INSTALL_WINDOWS.bat`: one-time **safe, idempotent** integration with your existing `company_kpi_metrics.py`, preserving all existing KPI tabs. If the expected current code is different, it refuses to edit it.
- Regression tests.

## Installation with GitHub Desktop

1. Extract the ZIP.
2. GitHub Desktop → Repository → Show in Explorer.
3. Copy **all contents** of the extracted package to the root of your repository, merging `scripts/`, `tests/` and `.github/` (do not create a second nested project folder).
4. Double-click `INSTALL_WINDOWS.bat` from the **repository root**. It inserts the ranking panel in `company_kpi_metrics.py`. It does not overwrite your `app.py`.
5. Return to GitHub Desktop, **do not commit** the optional `company_kpi_metrics.py.before_fundamental_rankings.bak` backup (you may move it outside the repo). Review the changes, commit, and Push origin.
6. GitHub → Actions → `USA Company Fundamentals, Quotes and Ranking Refresh` → Run workflow. The workflow will also run weekdays if Actions are enabled.
7. USA → USA Financial KPIs → **Fundamental Rankings**, above the existing company financial KPI form.

GitHub Actions must have `contents: write` permission and an existing `SEC_USER_AGENT` GitHub repository secret containing descriptive organization/name and contact email.

## Data outputs

- `data/fundamentals/sec_company_directory.json` and `facts_<CIK>.json`: SEC issuer directory and cached financial filing facts.
- `data/usa_research/quotes.csv`: dated Yahoo USD stock prices, market capitalizations and available quote multiples.
- `data/usa_research/company_research.csv`: existing company research dataset.
- `data/usa_research/fundamental_rankings.csv`: one verified company per row, all actual financial values, five individual ranks, sum, market cap (only for ties), and final rank.
- `data/usa_research/fundamental_field_evidence.csv`: ticker, source financial statement field, filing date, period end, accession, and value.
- `data/usa_research/financial_source_links.csv`: links to StockAnalysis, Finviz and Yahoo company pages with ticker inserted for **manual verification only**.
- `data/usa_research/fundamental_ranking_report.json`: coverage diagnostics, eligible and ineligible counts.

## Ranking policy

For companies with five available and comparable metrics:

1. Rank **ROE %** descending.
2. Rank **Current Ratio** descending.
3. Rank **Operating Margin %** descending.
4. Rank **Net Margin %** descending.
5. Rank **EPS growth %**, calculated from consecutive, positive annual diluted EPS values, descending.
6. **Total Fundamental Rank** = five metric ranks added together; smaller is better.
7. Only if two or more companies share the same total, use the **higher USD market capitalization** to break that tie. Market cap never changes the sum. If two tied companies have the same market cap, they share rank (ticker determines display order).

Financial companies (banks, insurers, REITs etc.) are omitted from this five-metric cross-industry ranking because liquidity and margins are not comparable. Their verified membership row remains in the output, marked unranked. Missing metric values remain NA; no scores are invented. Financial dates and original SEC concepts are preserved for audit. The liquidity convention currently ranks higher Current Ratio first; it may favor inefficient working capital and should be interpreted with context.

## Status and limitations

Offline Python parsing and targeted ranking tests passed, and YAML parsed. **This workflow has not been executed in the live GitHub repository or Streamlit deployment**. A workflow success is not equivalent to complete data coverage; some verified securities do not publish comparable SEC CompanyFacts records. Yahoo quote availability, SEC tagging and reporting periods also differ. No public-site scraping and no provider guarantees. Scores are a fundamental-research ordering, **not a valuation or investment recommendation**.

The workflow publishes datasets using a clean Git worktree, avoiding dirty-tree rebases. Do not run competing writer workflows simultaneously without respecting `concurrency: market-data-writer`.
