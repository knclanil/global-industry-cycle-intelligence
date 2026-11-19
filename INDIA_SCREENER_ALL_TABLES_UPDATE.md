# India Company Financial KPI Intelligence — Screener tables

At the bottom of the India KPI page, the Screener consolidated section now provides:

- Peer Comparison (only when the peer table is present in the accessible page HTML)
- Quarterly Results
- Profit & Loss
- Balance Sheet
- Cash Flow
- Ratios
- Shareholding Pattern, including distinct published yearly variants where available

The tables are extracted from the same already-retrieved consolidated Screener response used by the KPI page. No new endpoints are requested when changing tabs. Date-based columns sort chronologically and the history selector controls how many observations are shown; peer metadata is kept intact. Each available table can be exported to CSV. Percentages and price/ratio values retain their original units, and missing data is shown as unavailable. Missing dynamically loaded peer tables are not bypassed via undocumented endpoints.

## Deployment

Extract the `nightly_build` contents to the repository root; retain your existing `data/india_holdings` and `data/india_financials` generated caches and history. Push changes and restart Streamlit. Open India Company Financial KPI Intelligence, analyze a ticker, then scroll below KPI tabs to the Screener consolidated section.

## Source access

The existing Screener fetch respects HTTP errors and does not attempt to bypass 403, login or access controls. Reuse must comply with provider terms and permissions. No live source retrieval or Streamlit layout benchmark was performed in the build environment.
