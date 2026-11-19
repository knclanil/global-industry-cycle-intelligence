# India Fundamental Valuation — Original Reference Port

## What was ported
- `india_valuation_reference.py`: source-based implementation copied from the uploaded `factor-holdings-intelligence-main (9).zip` / `india_valuation.py`. All financial calculations, the per-metric NSE → Screener → Yahoo fallback, consolidated Screener financial tables, published ratios, peer-median industry P/E, annual fundamental derivation, PEG/PEGY, five-year normalized FCF, and Bear/Base/Bull DCF stay in place. One module-specific symbol normalizer is replaced with the existing application's validated NSE symbol normalizer.
- `india_fundamental_trends_reference.py`: original annual Yahoo revenue, profitability, leverage, liquidity and dividend-yield trend calculations and bar cards.
- `india_valuation_ui.py`: small navigation and ticker/holdings selector adapter; original valuation view is invoked unchanged.

## How data is fetched
- NSE public quote: last price, reported company P/E, sector P/E if present.
- Screener consolidated `/company/SYMBOL/consolidated/`: Profit & Loss, Balance Sheet, Cash Flows, Ratios, Quarterly Results, peer median and available top ratios. Requests may fail due to source access restrictions. Do not attempt to evade restrictions.
- Yahoo `.NS`: price, shares outstanding, dividend yield, quote multiples, annual CFO and dedicated capex lines. Financial history uses Yahoo income, balance, dividends and price records.
- Missing values remain N/A and individual source failures are shown. Requests are made only after clicking Analyze company / Load annual financial trends; Streamlit data caching applies.

## Source fidelity and limitations
- The original reference `dcf_per_share()` assumes starting cash flow is FCFE, while the automatic calculation uses the proxy CFO less capex. The UI deliberately labels this provisional and not fully reconciled FCFE.
- Yahoo can return incomplete or currency-unknown data; the original engine rejects unverified quote currency rather than treating it as INR.
- Screener access must comply with site terms and restrictions; source 403 may produce N/A. A script cannot guarantee the site's access.
- This is a valuation-methodology port, not a replacement for the separate India Company Financial KPIs or holdings analysis pages.

## Install and deploy
Install from `requirements.txt`, keep `data/india_holdings` snapshots, and deploy with the existing app entry point. Select **India Fundamental Valuation**. No new key is required for Yahoo or Screener; provider access is not guaranteed.
