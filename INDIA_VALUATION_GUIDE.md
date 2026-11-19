# India Fundamental Valuation

This page adapts the scenario valuation framework from the user-provided **Factor Holdings Intelligence** project (`india_valuation.py`) to the Global Industry Cycle Intelligence dashboard. The reference's three five-year assumptions are preserved:

| Scenario | Annual growth | Required return | Terminal growth |
|---|---:|---:|---:|
| Bear | 0% | 12% | 2% |
| Base | 3% | 11% | 3% |
| Bull | 5% | 10% | 3.5% |

## Data and setup

- **NSE**: security IDs and memberships come from the India Holdings refresh. The page links to the live NSE quote but does not secretly ingest live NSE quote data.
- **Yahoo Finance**: on-demand *single company* annual statements and market quote, or files pre-populated by the GitHub Actions India financial workflow. Use `.NS` symbols. Refresh is explicitly button-triggered, not performed on ordinary Streamlit rerenders.
- **Screener.in**: direct consolidated-financial-statements link. This implementation does not scrape/reproduce Screener data or assume the linked report and Yahoo statements are identical.
- The engine contains an explicit source-priority helper to support future approved feeds, but the current page uses Yahoo for numeric valuations. NSE and Screener are **references** for manual cross-checking, not automatically merged providers.

**Company lookup:** company directory, or enter NSE symbol directly; choose an annual fiscal period. If Yahoo returns empty data, the page explains missing coverage rather than inventing figures.

## Calculations

- Free cash flow is annual operating cash flow minus absolute capital expenditure. The model uses the latest three to five **consecutive** annual observations through the chosen fiscal period, including negative observations. Historical financial statement periods are not selected from dates after the chosen fiscal period.
- Provisional five-year DCF: sum the present value of annual projected cash flows plus terminal value using the Gordon growth model, divide by period-appropriate shares (with explicitly labeled quote-share fallback). It is **not** certified FCFE/FCFF or a fair-value guarantee.
- Margin of safety = `(DCF per share - market share price) / DCF per share`. 25% margin-of-safety reference price is `DCF × 0.75`.
- Graham Number = `sqrt(22.5 × positive diluted EPS × positive book value per share)`.
- An optional user-selected earnings price is `positive EPS × assumed P/E`; PEG = P/E divided by **five-year historical EPS CAGR in percentage points**. PEGY requires a verified dividend yield and is not displayed if it is missing.
- Book value, tangible book value, NCAV and hypothetical liquidation values use the existing India financial KPI engine. Unknown preferred-equity claims are **not assumed to be zero** unless the user explicitly opts into that assumption.

## Critical limitations

- Financial statement consolidation scope is not independently confirmed for Yahoo. Always compare the source with Screener consolidated filings and official company announcements before relying on it.
- Company financial firms (bank/insurer/NBFC) need specialized methodologies; the page flags them and does not label ordinary free-cash-flow DCF as a dependable bank valuation.
- Current market quotes and historical report dates differ, and quote currency must match the reported financial currency for margin-of-safety comparisons.
- Source retrieval can be blocked or data may be incomplete. Existing saved records remain accessible. Missing data is N/A, not 0.
- This release adds **valuation research**, not trading recommendations, nor full automatic NSE/Screener financial-statements scraping.
