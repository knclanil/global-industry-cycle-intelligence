# India Company Financial KPI Intelligence

This new compact page replaces the former **India Company Financial KPIs** page and its on-demand Yahoo-only UI code. The original **India Fundamental Valuation** page remains untouched, as does the NSE sector/factor group analysis and the US SEC financial KPI page (now clearly labelled **USA Company Financial KPI Intelligence**).

## Data method

Copies/reuses the data collection and metric calculations in `india_valuation_reference.py` (the port from the user's Factor Holdings Intelligence reference project): NSE quote → Screener consolidated financial statements → Yahoo Finance for each available market metric; yahoo annual CFO/capex is a separate source for provisional DCF. Provider requests only run when **Analyze financial KPIs** is selected. A failure in one provider will not conceal available values from another.

## User interface

**Overview; Growth & Margins; Balance Sheet; Cash Flow; Value & Intrinsic; Annual / Quarterly Trends; Sources & Diagnostics.** Metric tiles show compact Indian-unit formatted currency, sources, and clear N/A placeholders. Financial statement amounts are in **₹ crore** (Screener reports ₹ crore). Quote price and earnings per share are ₹, current shares are counted in crore. Example: 12,345.67 INR crore displays `₹12,345.67 Cr`, not `₹123.46B`. Numerical values are comma-grouped throughout.

The default valuation and quality indicators come from the source project's reference calculations; cash flow DCF is provisional and can be inapplicable to banks/NBFCs. Graham Number is an additional screening metric and needs positive EPS and book equity per share. Consolidated Screener and Yahoo report scope and dates may differ; these are not automatically reconciled.

## Data rights and access

Provider availability and the right to reuse data on a public dashboard must be verified. No anti-bot bypass is implemented. Screener may reject automated requests. All absent data remains N/A. If only Yahoo market quotes are accessible, statement charts may be empty and provider errors will be listed.

## Deployment

Copy the `nightly_build/` directory contents into the repo root, preserving `data/india_holdings` and `data/india_financials`. Delete old tracked files only if obsolete; the sector-level financial pipeline still needs `india_financial_data.py` and `scripts/refresh_india_financials.py`. Restart Streamlit.
