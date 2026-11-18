# Global Sectors — Methodology and Data Wiki

## Coverage and benchmark

Global Sectors compares ten **US-listed, USD-denominated global sector ETFs** against **ACWI**, the iShares MSCI ACWI ETF (broad developed- and emerging-market equities). The sector ETF set is not a complete, perfectly harmonized GICS sector universe. Currency, fees, tracking differences, and ETF exposure can affect comparisons.

| Sector | ETF |
|---|---|
| Technology | IXN |
| Financials | IXG |
| Healthcare | IXJ |
| Energy | IXC |
| Consumer Staples | KXI |
| Consumer Discretionary | RXI |
| Industrials | EXI |
| Materials | MXI |
| Utilities | JXI |
| Communication Services | IXP |

## Source and data controls

Historical OHLCV and adjusted closing prices are downloaded through **Yahoo Finance / yfinance**. Data are cached for one hour and can be manually refreshed. Adjusted closes are used for all calculations. Missing sector series are flagged; ACWI is mandatory. A PASS status indicates internal data-quality checks only, **not independent verification** against ETF issuer prices.

The sector selector supports one, multiple, or all sectors. Relative Time controls the strength lookback; From/To dates control chart display and cumulative returns. Calculations use additional pre-start history for warm-up.

## Relative rotation map

Let P_s(t) be the adjusted closing price of a global sector ETF and P_b(t) be ACWI adjusted closing price. Set Q(t) = P_s(t)/P_b(t).

- **Relative strength (%)** = 100 × [Q(t)/Q(t−L) − 1].
- **RS momentum (percentage points)** = RS(t) − RS(t−M), where M = max(2, floor(L/2)).
- L is the number of trading sessions selected: 1W=5, 2W=10, 4W=20, 1M=21, 3M=63, 6M=126, 12M=252.

Quadrants: **Leading** RS≥0 and momentum≥0; **Improving** RS<0 and momentum≥0; **Weakening** RS≥0 and momentum<0; **Lagging** RS<0 and momentum<0.

Only one historical sector movement path is shown at a time to prevent overlap. The spline is **visual interpolation**, not synthetic observations. All selected sector endpoints remain visible.

## Sector performance

Period sector return (%) = 100 × [P_s(end)/P_s(start) − 1]. Benchmark return uses the same formula for ACWI. **Excess vs ACWI (percentage points)** = sector return − benchmark return.

## Sector trends vs ACWI

For each selected sector, on each date t:

**Trend(t) = 100 × [P_s(t)/P_s(start) − 1] − 100 × [P_b(t)/P_b(start) − 1].**

All lines start at **0 percentage points** on the first selected trading session. Positive values indicate cumulative outperformance against ACWI; negative values indicate underperformance. This is a difference of cumulative returns, not the compounded return of a long-short portfolio.

## Validation and limitations

The dashboard checks benchmark availability, valid adjusted closes, duplicate dates, missing sessions, recent session coverage, and large daily price changes. Sector problems are shown as warnings; missing or invalid benchmark data prevents classifications. Yahoo data may be delayed or revised. No independent provider reconciliation or investment recommendation is implied. The USA daily GitHub Actions check does not automatically validate Global Sectors.


## Data-quality interpretation and known gaps

**PASS** means the available downloaded series passed the implemented internal checks; it does **not** certify complete historical coverage, zero exchange-calendar gaps, or agreement with an independent official source. **WARNING** flags concerns without necessarily suppressing every valid sector. **FAIL** prevents calculations when required benchmark data cannot be trusted. Unavailable sector histories may be excluded from the output, so verify which sectors appear in the classification table.

The app has **not completed a live, all-symbol, exchange-calendar-aware gap audit** for Global, USA, and India, and does not perform independent price reconciliation. Missing weekday observations may be exchange holidays; historical coverage and as-of dates can vary by provider. The scheduled GitHub workflow checks **USA only**; it does not validate India or Global on a schedule.
