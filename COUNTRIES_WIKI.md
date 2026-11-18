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

---

## Worked calculation guide — Global Countries

This section explains the **actual zero-centered relative-strength model** used by the application, with illustrative numbers. The figures below are examples only, **not live market observations**. The same formulas apply to each selected country ETF relative to **ACWI**.

### 1. Inputs and time windows

- **Analytical price `P`**: the adjusted closing price when available and applicable; certain NSE indices instead use published index closing levels. The benchmark must use observations from the same sessions.
- **Relative Time (`L`)**: `1W=5`, `2W=10`, `4W=20`, `1M=21`, `3M=63`, `6M=126`, `12M=252` **trading observations**. `M=max(2, L//2)` is the momentum lag. For `1M`, `L=21` and `M=10`.
- **From Date / To Date**: control the displayed performance interval, trends, and final classification date. Relative Time controls the *indicator lookback*, not the chart's start date. The application fetches earlier history to warm up the indicators.
- **Data alignment**: observations are aligned by available session dates. Missing history can remove an instrument from the analysis; missing or invalid benchmark data can prevent classifications. Missing values must not be interpreted as zero returns.

### 2. Relative price ratio — what are we comparing?

For an instrument `A` and benchmark `B` (ACWI):

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

**Example:** if the instrument rises from **100 to 108** (`+8%`) and ACWI rises from **200 to 210** (`+5%`), excess performance is `8−5=+3 pp`. If the instrument falls `−4%` and the benchmark falls `−2%`, excess performance is `−4−(−2)=−2 pp`.

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

For ETFs, the analysis uses the adjusted closing price supplied by Yahoo Finance. This is a provider-adjusted return proxy, not an independently audited total-return series.
