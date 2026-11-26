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

---

## Worked calculation guide — Global Sectors

This section explains the **actual zero-centered relative-strength model** used by the application, with illustrative numbers. The figures below are examples only, **not live market observations**. The same formulas apply to each selected Global sector ETF relative to **ACWI**.

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
