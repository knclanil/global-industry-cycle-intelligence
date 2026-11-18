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

