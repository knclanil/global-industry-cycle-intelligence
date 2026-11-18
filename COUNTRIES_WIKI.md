# Global Countries — Methodology and Data Guide

## Purpose and coverage
Compare **20 country equity ETF proxies** against **ACWI** (iShares MSCI ACWI ETF) using the same relative rotation, performance, and trend methodology as the sector dashboards. All ETFs are US-listed and USD-denominated; this is **not** a direct comparison of local-currency country indices. Country funds differ in fees, index methodology, investable coverage, and currency exposure.

| Country | ETF | Country | ETF |
|---|---|---|---|
| United States | SPY | India | INDA |
| Japan | EWJ | China | MCHI |
| United Kingdom | EWU | Germany | EWG |
| France | EWQ | Switzerland | EWL |
| Canada | EWC | Australia | EWA |
| South Korea | EWY | Taiwan | EWT |
| Brazil | EWZ | Mexico | EWW |
| South Africa | EZA | Indonesia | EIDO |
| Thailand | THD | Malaysia | EWM |
| Saudi Arabia | KSA | United Arab Emirates | UAE |

## Source and benchmark
Historical adjusted closes are retrieved from **Yahoo Finance via yfinance**. ACWI is the required benchmark. No independent exchange/issuer reconciliation is performed. Provider availability and historical coverage can vary.

## Filters
**Countries** allows all, one, or multiple selections. **Relative Time** maps 1W, 2W, 4W, 1M, 3M, 6M, 12M to trading-session lookbacks. **From Date → To Date** controls displayed history and period returns; calculations load additional warm-up history.

## Relative rotation calculations
For country adjusted close `P` and benchmark adjusted close `B`, define `Q(t) = P(t) / B(t)`.

- **Relative strength (%)** = `100 × (Q(t) / Q(t−L) − 1)`.
- **Momentum (percentage points)** = `RS(t) − RS(t−M)`, where `M = max(2, L//2)`.
- **Leading:** RS ≥ 0, momentum ≥ 0.
- **Improving:** RS < 0, momentum ≥ 0.
- **Weakening:** RS ≥ 0, momentum < 0.
- **Lagging:** RS < 0, momentum < 0.

These are custom descriptive measures, **not** proprietary RRG indicators or forecasts. The map uses a smooth visual spline for the selected country's path, but underlying observations are unchanged. One movement path is shown at a time to limit overlap.

## Performance and trends
- **Country return (%)** = `100 × (P(end)/P(start) − 1)`.
- **ACWI return (%)** = `100 × (B(end)/B(start) − 1)`.
- **Excess return (percentage points)** = country return minus ACWI return.
- **Relative trend (percentage points)** at date `t` = `100 × (P(t)/P(start) − 1) − 100 × (B(t)/B(start) − 1)`.

Every trend begins at **0** on the first common selected trading session. Above zero means outperformance versus ACWI, not necessarily a positive absolute return.

## Validation and limitations
The application checks benchmark availability, positive adjusted closes, duplicates, missing fields, gaps against ACWI sessions, outlier returns, and freshness. Unavailable or invalid country series are excluded; an invalid benchmark stops the analysis. PASS indicates internal consistency only, **not proof of zero gaps or independent price accuracy**. The scheduled GitHub Action currently checks USA data only. Yahoo Finance availability and ETF inception dates may restrict long histories. No database is used.
