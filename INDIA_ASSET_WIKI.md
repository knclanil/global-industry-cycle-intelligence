# INDIA Asset Flow — Cross-Asset Rotation

## Purpose
Identify **relative price leadership** among asset classes. This dashboard **does not measure actual investor net inflows or outflows**. Its title is a navigation label, not a claim of verified money flows.

## Universe and benchmark
Benchmark: **Nifty 50**. Instrument definitions and ticker mapping are maintained in `india_asset_market_data.py`.

Prices are ETF/index proxies, not pure asset-class total-return series. ETF currency, duration, dividends, index composition, expense ratios and liquidity may differ. ETF volume is not net subscriptions. Adjusted close is used when supplied by the provider.

## Calculations
Q = asset adjusted close / benchmark adjusted close.

Relative strength = 100 × (Q / Q shifted L sessions − 1).

Momentum = relative strength − relative strength shifted M sessions, M = max(2, L // 2).

Relative performance = cumulative asset return − cumulative benchmark return (percentage points); displayed trends start at zero on the selected first session.

Leading: RS ≥ 0 and momentum ≥ 0; Improving: RS < 0 and momentum ≥ 0; Weakening: RS ≥ 0 and momentum < 0; Lagging: both negative.

## Market regime
Heuristic only: Risk-on requires at least two positive excess-return risk-sensitive proxies and more positives than defensive proxies; Defensive uses at least two defensive positives; inflation-sensitive leadership uses at least two gold/commodity positives. Otherwise Mixed/unconfirmed. The rules do not establish macroeconomic causes or predict returns.

## Availability and validation
Missing instruments are excluded. Missing or invalid benchmark is fatal. No artificial data or forward fills are used. Provider structural checks are not independent price verification. Live market availability is not guaranteed.


## Government bonds: verified-source fallback logic
The India Asset Flow government-bond key is `NIFTY_GSEC_10Y` (a logical dashboard identifier, **not** a Yahoo ticker). The loader first attempts the Nifty 10-year benchmark G-Sec index through NSEPythonServer and the NSE historical-index API using candidate NSE names. The accepted name and live data availability are **not independently confirmed**. Only structurally valid OHLC observations are accepted.

If no valid index series is retrieved, the loader attempts Yahoo Finance `SETF10GILT.NS` as a government-bond ETF fallback. If both fail, government bonds are excluded and no data are fabricated. The index and ETF histories are **never spliced together**. An NSE price index uses its Close as the analytical price and is **not a total-return series**; the ETF uses its provider-adjusted close. This methodology mismatch can materially affect rankings. The Data Table reports `Source`, `Instrument type`, `Return basis`, `Fallback used`, and `Underlying symbol` for each retrieved series. These are data-provenance labels, not independent confirmation of provider accuracy.
