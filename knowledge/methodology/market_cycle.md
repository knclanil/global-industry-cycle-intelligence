## Market-cycle methodology

Market stages are **price-based classifications**, not validated economic-cycle stages. For each monthly observation:

- `RS6 = (sector_close / sector_close_6_months_ago - benchmark_close / benchmark_close_6_months_ago) × 100` (percentage-point excess return).
- `RS3` uses three months.
- `Momentum change = RS3(current) − RS3(three months ago)`.
- **Leading:** RS6 ≥ 0 and momentum change ≥ 0.
- **Weakening:** RS6 ≥ 0 and momentum change < 0.
- **Improving:** RS6 < 0 and momentum change ≥ 0.
- **Lagging:** RS6 < 0 and momentum change < 0.

Labels require sufficient observations; unavailable values are never silently filled. RSI uses exponentially smoothed gains/losses with 14-day Wilder-style alpha. Calculations are research screens, not predictive models.

### Fundamental cycle

Recovery / expansion / slowdown / contraction in **industry activity** requires independently sourced earnings, production, orders, capacity utilization, inventories and demand data. This first implementation does **not** claim to determine that stage.
