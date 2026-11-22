# USA and India Financial Research navigation — complete app.py

This replaces **only `app.py`**. It is based on the full previously supplied USA research navigation `app.py`, checked against the public GitHub `main/app.py` navigation and rendering branches on November 21, 2026.

## USA sidebar
1. USA Asset Flow
2. USA Sector
3. USA Factors
4. Investment Opportunity Screener
5. Company Deep Dive
6. USA Financial Research (existing `company_financial_research.py`)
7. USA Financial KPIs (existing `company_kpi_metrics.py`)

## India sidebar
1. India Asset Flow
2. India Sector
3. India Factors
4. Investment Opportunity Screener
5. Company Deep Dive
6. India Financial Research (existing `india_financial_ui.py` previously titled India Sector & Factor Financials)
7. India Financial KPIs (existing `india_kpi_intelligence.py`)

The old shared COMPANY FINANCIALS section retains Fundamental Quality Rankings and India Valuation. No financial collector, Knowledge Graph or dashboard data code is changed.

## Install
Extract the ZIP. Copy `app.py` into the ROOT of your `global-industry-cycle-intelligence` GitHub Desktop working folder and replace the old `app.py`. Commit and push. No installer scripts and no additional dependencies.

**Note:** India Financial Research links to the existing *India Sector & Factor Financials* renderer; it does not create a new statement-by-statement UI. The USA page uses the existing detailed company financial renderer.

## Checks
Python AST syntax passed. Unique navigation page keys, both regional financial page mappings, and expected render branches were checked. Not runtime-tested on Streamlit Cloud.
