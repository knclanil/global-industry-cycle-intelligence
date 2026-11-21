# India Financial Intelligence — complete end-to-end pipeline

**Scope:** data collection → cached snapshots → normalized company KPI exports → coverage diagnostics → verified NSE sector/factor membership join → data-quality gates → within-industry financial/valuation comparisons → Streamlit opportunity explorer → GitHub Actions daily publishing.

This is a complete implementation of that *technical pipeline*, not a claim that Yahoo Finance provides complete Indian financial statements. Missing source data stays missing and some or all firms may have blank scores until an authorized provider can supply statement data. No Screener.in scraping or unauthorized financial data is included.

## Install into `global-industry-cycle-intelligence`

1. Unzip and merge its **`scripts/`, `tests/`, `.github/`, and `india_opportunity_ui.py`** into the corresponding locations in the root of your local GitHub Desktop checkout. **Do not copy README into the main repo unless you wish.**
2. From **GitHub Desktop → Repository → Open in Terminal**, run **`python scripts/install_india_opportunity_ui.py`** once. This safely inserts an **Investment Opportunities** tab into the existing **India Sector & Factor Financials** page and keeps every existing tab intact. It only changes `india_financial_ui.py`, not the Knowledge Graph or navigation. If the original page has changed since this patch, the installer refuses to alter it.
3. Commit/push all new and changed source files using GitHub Desktop. Do not commit your locally generated financial data unless explicitly desired; the workflow handles that.
4. Under GitHub Actions, open **India Company Financials Refresh → Run workflow**. Initially set `symbols=RELIANCE,TCS,INFY`, `limit=10`. Later leave symbols blank and use `limit=25` to rotate through the verified constituent universe, or `audit_only=true` to rebuild outputs without Yahoo traffic.
5. After Action succeeds, open **India Sector & Factor Financials → Investment Opportunities** in Streamlit. The screen reads committed files, never fetches statements synchronously.

## File manifest

- `scripts/india_financial_pipeline_v2.py` — batch Yahoo collection, label-compatibility layer, conservative refresh/rebuild and KPI audit (reuses your existing `scripts/refresh_india_financials.py` and `india_financial_data.py`).
- `scripts/build_india_opportunity_dataset.py` — **NEW:** identity-safe NSE/financial join, sector and factor memberships, freshness validation, industry-aware financial comparisons, exports and report.
- `india_opportunity_ui.py` — **NEW:** cached read-only Streamlit screener with multi-select sector/factor filters (ANY or ALL within each filter; AND between them), readiness and ranking views, source evidence and CSV download.
- `scripts/install_india_opportunity_ui.py` — **NEW:** idempotent installer for existing financial page tab; refuses unexpected source structure.
- `.github/workflows/india-financials-refresh.yml` — **REPLACE:** single existing refresh workflow, batch scheduling, tests, audit, dataset build, output validation and clean-worktree commit/push.
- `tests/test_india_financial_pipeline_v2.py` — batch/audit normalization tests from preceding patch.
- `tests/test_india_opportunity_pipeline.py` — **NEW:** membership deduplication, score data gates, stale-data protection, peer sufficiency, UI installer tests.

## Published outputs

Existing outputs remain:

- `data/india_financials/companies/*.json`: source snapshots and provider metadata;
- `data/india_financials/refresh_status.csv`: per-symbol collection errors/status;
- `data/india_financials/company_financial_summary.csv`: one verified company with available KPI values;
- `data/india_financials/index_financial_summary.csv`: source index financial aggregates;
- `data/india_financials/build_summary.json`: collection status.

New outputs:

- `data/india_financials/kpi_coverage_report.json`: actual usable core-KPI coverage;
- `data/india_financials/kpi_coverage_by_company.csv`: metric-by-metric missing fields;
- `data/india_financials/opportunity_research.csv`: one verified NSE company per row, memberships, freshness, finances, rankings if eligible;
- `data/india_financials/opportunity_build_report.json`: counts of readiness/scoring and model limitations.

## Scoring and data policy

- Company joins are by `company_key` (ISIN-derived when published); **not** by fuzzy company names.
- Only direct NSE constituent edges enter the verified grouping; factor families and sector index memberships are deduplicated. The industry is from NSE's company file, not inferred from the factor label.
- Industry-aware scoring requires at least **five OTHER** companies with valid comparable metric values. Financial institutions get distinct ROE and P/B/P/E handling and are never compared on industrial operating margin/leverage.
- Fresh financial period ≤540 days; quote retrieval ≤30 days (quote timestamp is *retrieval time*, not official trade time). No score unless financial + valuation input gates and all 3 score components pass.
- Component percentages reflect within-group percentiles, **not** predicted performance or absolute intrinsic value. Research score = **45% Quality + 20% Growth + 35% Valuation**. **Market positioning/rotation is not yet integrated into this score**, since doing so without a verified company-to-price-rotation data contract would misrepresent results. Existing Sector and Factors pages remain unchanged.
- Peer medians/percentiles can be unreliable if the peer cohort is tiny, incomplete, or biased toward Yahoo's available companies. Output is a *research triage score only*.
- No invented financials, zero substitutions, scraped Screener data, inferred NSE weights, or automatic investment recommendations.

## Test commands

With requirements installed in the real repo:

```bash
python -m unittest discover -s tests -p 'test_india_financial_pipeline_v2.py' -v
python -m unittest discover -s tests -p 'test_india_opportunity_pipeline.py' -v
python scripts/india_financial_pipeline_v2.py --audit-only
python scripts/build_india_opportunity_dataset.py
```

In this preparation environment, the five new standalone logic tests pass and Python/YAML syntax is checked, but existing collection tests and live Yahoo/Streamlit integration cannot be exercised without a full local checkout and network access. GitHub Actions will run both test files against the actual repository.

### Troubleshooting

- **0 scored companies:** This is valid when Yahoo responses lack KPIs or quotes are stale. Inspect `kpi_coverage_report.json`, `refresh_status.csv`, and `opportunity_build_report.json` rather than forcing scores.
- **No Opportunity tab:** Run the installation script, commit its update to `india_financial_ui.py`, and push.
- **Workflow denied push:** Check repo Settings → Actions → General → Workflow permissions: Read and write.
- **Workflow fails tests:** Share the Actions log; do not assume a successful publish. The package does not replace or duplicate source financial collection scripts.
