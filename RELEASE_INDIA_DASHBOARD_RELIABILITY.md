# India and USA financial dashboard reliability update

## Navigation
- Global Capital Intelligence Network is isolated under **Knowledge Graph**.
- Research pages have their own **Company Financials** section.
- Active sidebar button uses the primary style (cyan left border and darker blue highlight); other pages remain muted.

## Company financials
- Both USA Company Financial KPI Intelligence and India Company Financial KPI Intelligence include a dark-theme, period-aligned **Revenue → Net Income** Sankey.
- USA uses verified SEC annual statement fields for the selected year.
- India uses Screener consolidated Profit & Loss annual values when available; cost/tax residuals are *derived*, not falsely labelled as published expense lines.
- The India **Sources & Diagnostics** tab shows source availability separately from raw request success, consolidated table coverage, per-metric provenance and access errors.
- Screener **Ratios** display tab is titled **Financial Ratios & Efficiency**. The source table key remains unchanged.
- The peer table searches visible published HTML in several permissible page layouts. If no peer table is returned, the tab displays **NSE shared-sector constituents** as an explicitly different comparison, with any saved Yahoo metrics; it does not invent Screener peers.

## NSE source / overlap / financial analysis
- Rankings and overlap tables are generated **in memory from verified saved `constituents.csv`** if the generated ranking exports are missing. This avoids a blank page after a successful 31-index data refresh, but production should still run the precomputation workflow.
- Sector and factor financial aggregates are derived from saved constituent memberships and the financial records actually present, rather than depending on a separately generated index summary CSV. The tables remain visible even if no financial provider data has yet been collected.
- A missing company financial summary can be reconstructed from previously saved company JSON snapshots.
- Companies researched using Screener in the current Streamlit session can contribute their explicitly sourced, available metrics to the sector/factor summaries. These readings are session-only, **not** persistent coverage, and missing values remain missing.
- Index source/browser coverage rendering tolerates absent status files and nonnumeric constituent counts while displaying verified source membership records.

## Data requirements / limitations
- Generated NSE constituent snapshots and financial snapshots **are not included in this code ZIP**. Preserve `data/india_holdings` and `data/india_financials` from the deployed repo, then run both GitHub Actions refresh workflows.
- A live NSE 403, missing Screener peer table, or Yahoo financial-data shortfall cannot be fixed with visual formatting. No code bypasses provider access restrictions.
- No metric is fabricated, no holdings weights are inferred, and all sector/factor fundamentals are **unweighted medians** of companies with a verified observation.
- Full universe populated financials depend on usable persisted company financial snapshots from the background collector. Display of one company in Streamlit does not imply all 328 have data.
- This package is validated with Python compilation, 59 India test cases and a synthetic offline aggregation smoke test. Live Streamlit rendering and live provider collection were not tested.

## Useful verification steps
1. Run **India NSE Constituents Refresh** and ensure `data/india_holdings/constituents.csv` contains all 31 validated sources.
2. Run **India Company Financials Refresh** and confirm `data/india_financials/company_financial_summary.csv` is committed with nonempty `financial_period`, `revenue`, `net_income`, and source timestamps.
3. Restart Streamlit (for changed code), open India Overlap & Leadership and verify that the source-index matrix and heatmap render without downloaded ranking exports.
4. Open India Sector & Factor Financials, check coverage per index and inspect a specific index (e.g., Nifty IT).
5. Open the USA and India KPI Overview tabs to view the revenue flow diagram; open India KPI Sources & Diagnostics for explicit provider status.
