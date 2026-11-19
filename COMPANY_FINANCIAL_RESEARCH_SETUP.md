# Company Financial Research integration

Adapted from the user-provided Factor Holdings Intelligence ZIP (`financial_research_ui.py`, `sec_financials.py`, `value_research.py`, `market_reference.py`).

## Use
- Open **Global Intelligence → Company Financial Research**.
- Enter a US SEC-reporting ticker and click **Load company financials**.
- Browse Financial Overview, Income Statement, Balance Sheet, Cash Flow, Business Quality, and Conservative Value.
- Market-price lookup is optional and only starts after selecting its checkbox.

## SEC identity
Set `SEC_USER_AGENT` in Streamlit Cloud secrets or environment, e.g. `CompanyResearch/1.0 contact: real-email@domain.com`. The app checks both.

## Data and limitations
- SEC financials are sourced from companyfacts; existing `data/fundamentals/facts_<10-digit CIK>.json` are reused where available.
- The initial SEC ticker registry fetch may take time; cached copies are used on subsequent visits.
- This dedicated page does not bulk-process ETF holdings, reducing initial load.
- Buffett/Graham checks are heuristics, not validated investment recommendations.
- Non-SEC global issuers and full peer-relative investment rankings are not implemented here.
- Existing Fundamental Intelligence page remains unchanged.
