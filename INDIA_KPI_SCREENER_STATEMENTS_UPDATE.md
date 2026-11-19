# India Financial KPI Intelligence — Screener Statements

The **India Company Financial KPI Intelligence** page now shows the original consolidated **Balance Sheet** and **Cash Flow Statement** tables at the bottom of the page, below the seven existing tabs.

## Usage

Select an NSE symbol and click **Analyze financial KPIs**. After the usual KPI tabs, scroll to **Consolidated Balance Sheet & Cash Flow**. Select 5, 8, 12 years or all available periods. The tables retain the original row labels, show historical reporting periods in ascending date order, format amounts with thousands separators (INR crore), display missing entries as N/A, and offer CSV exports and a link to Screener.

## Data source and limitations

This feature displays **the Screener consolidated tables already retrieved by the existing on-demand reference provider**. It **does not issue additional HTTP requests**, scrape in bulk, bypass access restrictions, or fabricate financial results. Screener retrieval may be unavailable or disallowed depending on network access and source terms; in that case, the respective section displays an informative message rather than substituting Yahoo statement rows. For some companies there may be no consolidated statements. The page reports its retrieval timestamp when present. These source-reported figures should be verified against official filings before investment decisions.

## Files changed

- `india_kpi_intelligence.py`: added the two source tables at page bottom.
- `india_screener_statements.py`: date sorting, safe number formatting, original row labels.
- `tests/test_india_screener_statements.py`: unit tests.

## Deployment

Copy the contents of `nightly_build/` to the repository root and preserve existing `data/` directories. Commit and deploy the Streamlit application. This change does not alter the background pipeline, sector/factor analysis, or page navigation.
