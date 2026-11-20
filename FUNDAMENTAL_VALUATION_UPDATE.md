# Fundamental Quality Rankings — Intrinsic Value & Graham Update

This adds a **separate Intrinsic & Graham value** tab to **Fundamental Quality & Consistency**, preserving all existing quality-rank scores and keeping the three regional universes independent.

## Calculation sources

- **USA and SEC-reporting Global:** locally cached SEC Company Facts annual financials. Shares are sourced from annual weighted-average diluted or basic share count tags, with a labeled reported balance-sheet share-count fallback. No website EPS ratios are used.
- **India:** previously collected Yahoo annual financial statement snapshots. The earnings statement's `Diluted Average Shares` or `Basic Average Shares` is used when available; `Ordinary Shares Number` from the annual balance sheet is a labeled period-end approximation. No live requests are made while viewing rankings.
- **Calculated EPS** = reported annual net income attributable to common shareholders / reported annual weighted-average shares (or labeled period-end fallback). Cash flow is **not** earnings, so EPS cannot be computed from cash. **FCF / share** is separately calculated from (operating cash flow − absolute capital expenditure) / shares.
- **Book value/share** = reported common equity / shares, reducing equity for explicit preferred claims when present.
- **Graham Number** = sqrt(22.5 × calculated EPS × book value/share), only if both values positive.
- **DCF values**: 5-year discounted, normalized historic FCF proxy per share (bear/base/bull defaults 0%/12%/2%; 3%/11%/3%; 5%/10%/3.5% for forecast growth/discount rate/terminal growth). Requires three consecutive positive cash-flow years and reported shares. **This is a provisional FCF proxy, not verified FCFE and not an enterprise FCFF valuation**. Financial firms' generic FCF DCF is omitted.

All financial values are in the reporting currency per share (USD for US filings, INR for India snapshots); source periods and share-count bases are displayed. Unavailable inputs yield N/A, not zero. The valuation estimates never change the fundamental quality ranking formula.

## Refresh notes

The India share-count normalization now includes weighted-average share rows, which means **older cached snapshots may need a new background refresh** to populate reported weighted-average shares. If those are unavailable but period-end ordinary shares exist, derived EPS is explicitly labeled as an approximation. The app does not fetch financial reports synchronously in the rankings page.
