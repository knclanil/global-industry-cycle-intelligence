# MaketData → Global Industry Cycle (read-only integration)

Source inspected: MaketData-main (2).zip and global-industry-cycle-intelligence-main (1).zip. The existing app's Company Financial Research page is preserved and extended.

## Install
Copy `maketdata_bridge.py`, `maketdata_ui.py`, and `company_financial_research.py` into the root of Global Industry Cycle, replacing only `company_financial_research.py`. Add `pymongo>=4.6,<5` to the existing `requirements.txt` (do not replace that file). Commit and push. Existing Streamlit secrets `MONGODB_URI` and `MONGODB_DATABASE` are used. Set the Atlas user's database role to `read` and allow your deployment's network path.

Open Company Financial Research, load a company, then scroll to the MaketData section. Input multiple tickers separated by commas and click Fetch. The existing ticker is prefilled. Annual and quarterly normalized records are retrieved in one batch query per collection. No database writes.

## Scope and limitations
This is a tested integration **foundation**, not a verified production deployment. Live Atlas connectivity was not tested; secrets are inaccessible here. The MongoDB schema is inferred from MaketData source code; actual deployed document structure must be checked. Existing financial research remains available. Comparison, annual/quarterly tables, selected-universe peer-relative category scores, and source-safe ratio calculations are implemented. The UI does not yet auto-load the full existing industry stock-selection set or compute industry-wide rankings. Valuation requires market-price/market-cap integration and will be N/A until supplied. Additional requested ratios (ROIC, interest coverage, EV/EBITDA, net debt/EBITDA, consistency) require validated inputs not currently in this adapter. No score is assigned when any category is insufficient.

## Tests
`python -m unittest -v test_maketdata_bridge.py`

## Security
Never commit a real MongoDB URI or secrets. Use a read-only database account. This module calls only `find` on companies, financial_annual, financial_quarterly.
