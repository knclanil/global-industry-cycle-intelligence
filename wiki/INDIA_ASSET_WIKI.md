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

---

## Worked calculation guide — India Asset Flow

This section explains the **actual zero-centered relative-strength model** used by the application, with illustrative numbers. The figures below are examples only, **not live market observations**. The same formulas apply to each selected Indian asset-class proxy relative to **Nifty 50**.

### 1. Inputs and time windows

- **Analytical price `P`**: the adjusted closing price when available and applicable; certain NSE indices instead use published index closing levels. The benchmark must use observations from the same sessions.
- **Relative Time (`L`)**: `1W=5`, `2W=10`, `4W=20`, `1M=21`, `3M=63`, `6M=126`, `12M=252` **trading observations**. `M=max(2, L//2)` is the momentum lag. For `1M`, `L=21` and `M=10`.
- **From Date / To Date**: control the displayed performance interval, trends, and final classification date. Relative Time controls the *indicator lookback*, not the chart's start date. The application fetches earlier history to warm up the indicators.
- **Data alignment**: observations are aligned by available session dates. Missing history can remove an instrument from the analysis; missing or invalid benchmark data can prevent classifications. Missing values must not be interpreted as zero returns.

### 2. Relative price ratio — what are we comparing?

For an instrument `A` and benchmark `B` (Nifty 50):

`Q(t) = P_A(t) / P_B(t)`

**Example:** at the end of the selected lookback, suppose `P_A=120` and `P_B=240`; then `Q(t)=120/240=0.50`. At the beginning of that lookback, suppose `P_A=100` and `P_B=220`; then `Q(t−L)=100/220≈0.454545`.

The **level** of `Q` is not a rating: a ratio of 0.50 is not intrinsically better than 0.25. We measure **how that ratio changes**.

### 3. Relative strength (RS) — horizontal rotation-map axis

`RS(t) = 100 × [Q(t) / Q(t−L) − 1]`

Using the example: `RS(t) = 100 × [(0.50 / 0.454545) − 1] = +10.00%`.

**Interpretation:** the instrument-to-benchmark price ratio increased by **10%** over `L` trading observations. This does **not** mean the instrument returned exactly 10%, nor does it mean it received a 10% fund inflow.

### 4. RS momentum — vertical rotation-map axis

`Momentum(t) = RS(t) − RS(t−M)`

Suppose RS calculated `M=10` sessions earlier was **+6.00%** and today's RS is **+10.00%**. Then `Momentum(t)=10.00−6.00=+4.00 percentage points (pp)`.

If the earlier RS had been **+13.00%**, today's momentum would instead be `10.00−13.00=−3.00 pp`: relative strength is still positive, but it is weakening. This is a **difference between two lookback-relative-strength readings**, not a daily return or a percentage change of momentum.

### 5. Quadrant classification — worked examples

| RS (%) | RS momentum (pp) | Quadrant | Practical reading |
|---:|---:|---|---|
| +10.0 | +4.0 | **Leading** | Outperforming and relative strength improving |
| −3.0 | +2.0 | **Improving** | Still underperforming, but relative strength recovering |
| +10.0 | −3.0 | **Weakening** | Still outperforming, but relative strength fading |
| −4.0 | −1.5 | **Lagging** | Underperforming and relative strength deteriorating |

Zero counts as nonnegative: `RS≥0` and `Momentum≥0` are Leading; `RS<0` and `Momentum≥0` are Improving; `RS≥0` and `Momentum<0` are Weakening; otherwise Lagging. The KPI cards **count eligible instruments** in each quadrant; they are not percentages of money invested.

### 6. Selected-period performance — horizontal bars and table

For the **first and last available trading sessions inside From/To**, `t0` and `t1`:

`InstrumentReturn = 100 × [P_A(t1)/P_A(t0) − 1]`

`BenchmarkReturn = 100 × [P_B(t1)/P_B(t0) − 1]`

`ExcessReturn (pp) = InstrumentReturn − BenchmarkReturn`

**Example:** if the instrument rises from **100 to 108** (`+8%`) and Nifty 50 rises from **200 to 210** (`+5%`), excess performance is `8−5=+3 pp`. If the instrument falls `−4%` and the benchmark falls `−2%`, excess performance is `−4−(−2)=−2 pp`.

**Important:** the bar-chart excess return uses the selected **From/To period**, whereas the quadrant uses the separate **Relative Time** lookback. A positive bar can therefore coexist with a Lagging quadrant (and vice versa).

### 7. Relative trend — why every line starts at zero

At each date `t` in the selected period:

`InstrumentCumulative(t) = 100 × [P_A(t)/P_A(t0) − 1]`

`BenchmarkCumulative(t) = 100 × [P_B(t)/P_B(t0) − 1]`

`RelativeTrend(t) = InstrumentCumulative(t) − BenchmarkCumulative(t)` **in pp**.

| Selected session | Instrument cumulative | Benchmark cumulative | Relative trend |
|---|---:|---:|---:|
| Start (`t0`) | 0% | 0% | **0 pp** |
| Intermediate | +3% | +2% | **+1 pp** |
| End (`t1`) | +8% | +5% | **+3 pp** |

A rising relative trend means the *performance gap* is widening in the instrument's favor; it does **not** necessarily mean its absolute price is rising. This trend is a **difference of cumulative returns**, not the `Q` ratio and not a sum of daily excess returns.

### 8. Movement trail, data checks, and interpretation limits

The Relative Rotation Map places each instrument at `(RS, Momentum)` on the latest eligible session. The selected instrument's historical points form the movement trail. Any smoothed curve between points is **visual interpolation**, not newly observed prices or a forecast.

The Data Table lets you inspect underlying observations, source labels, missing symbols, duplicate sessions, invalid prices, and CSV exports. Provider data checks can flag problems, but they do **not** independently verify prices against an exchange or guarantee uninterrupted history.

For Indian NSE price indices, the application may use the published index Close rather than dividend-reinvested total returns. ETF adjusted closes and index closes are **not equivalent return bases**. The Data Table provides provenance and fallback details where available.

### 9. Asset-flow label and market-regime examples

**These dashboards estimate asset rotation from prices; they do not measure actual investor subscriptions, redemptions, or net fund flows.** Higher ETF trading volume is also not evidence of net inflows.

The **Market Regime** badge is a heuristic based on the number of eligible asset proxies with **positive selected-period excess returns** versus the equity benchmark:

- **Risk-on:** at least two risk-sensitive proxies (e.g., equities, high yield, real estate) have positive excess returns, and that count exceeds the defensive-positive count.
- **Defensive:** at least two defensive proxies (e.g., government bonds, gold, cash) have positive excess returns, and that count exceeds the risk-sensitive-positive count.
- **Inflation-sensitive leadership:** at least two gold/commodity/silver proxies have positive excess returns, and that count exceeds the risk-sensitive-positive count.
- **Mixed / unconfirmed:** no rule is met, or data are too sparse. The code evaluates these rules **in that order**; overlapping groups such as gold may contribute to more than one count.

**Illustrative example:** if government bonds, gold and cash all beat the equity benchmark, while high-yield credit and real estate lag, the badge may indicate **Defensive**. This is a descriptive signal, **not** proof that money flowed into those assets or that a macroeconomic regime caused the moves. An equity benchmark compared with itself has zero excess return by construction.
