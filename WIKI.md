# Dashboard Wiki

**Global Industry Cycle Intelligence** is a US equity-sector rotation dashboard comparing 11 sector ETFs with **SPY** (the S&P 500 ETF). It is a descriptive, historical analytics tool, not an investment recommendation or a forward-return forecast.

## 1. Coverage and source

| ETF | Sector |
|---|---|
| XLC | Communication Services |
| XLY | Consumer Discretionary |
| XLP | Consumer Staples |
| XLE | Energy |
| XLF | Financials |
| XLV | Healthcare |
| XLI | Industrials |
| XLB | Materials |
| XLRE | Real Estate |
| XLK | Technology |
| XLU | Utilities |
| SPY | Benchmark: S&P 500 ETF |

**Data provider:** Yahoo Finance, retrieved using the Python `yfinance` package. The dashboard uses **adjusted daily closing prices** for all returns and relative indicators; OHLC and volume are downloaded for integrity checks. Adjusted prices may be revised by the provider, and their handling of distributions and corporate actions is not independently certified. This application does not query an independent second market-data provider.

## 2. Controls and effective dates

- **Select all sectors / SECTORS:** Include all 11 ETFs or choose one or more. This changes the plotted sector points, comparison bars, trend lines and classification table. SPY remains the benchmark even when it is not shown as a sector.
- **RELATIVE TIME:** Sets the trading-session lookback used to calculate relative strength and momentum; it does **not** set the displayed date range. Mapping: **1W = 5**, **2W = 10**, **4W = 20**, **1M = 21**, **3M = 63**, **6M = 126**, **12M = 252** trading sessions.
- **FROM DATE → TO DATE:** Defines the display period and the classification **as-of** date. The app uses the first and last available trading sessions *inside* the chosen calendar range. Weekends and exchange holidays therefore do not generate observations. The app also retrieves up to **600 calendar days before From Date** to warm up the indicators.
- **QUADRANT FILTER:** Shows only sectors in the chosen quadrant on the charts and table. The four KPI counts still describe the complete selected sector set, before this filter.
- **Show smooth movement path:** Toggles the historical rotation trail. **Path length (sessions)** chooses the maximum number of recent plotted observations: 5, 10, 20, 40 or 60. **Movement path for** chooses one sector. Only one trail is shown at a time to reduce overlapping paths; other sector endpoints remain on the map.
- **Refresh now:** Clears Streamlit's cached price download and reruns the dashboard. It does not force Yahoo Finance to publish a new session.

The app permits dates from **January 1, 2019** through the current date. Relative Time is independent of the From/To span: a 12M indicator can be shown as of the last day of a short selected period if sufficient earlier data is available.

## 3. Relative rotation map: exact model

This is an **original zero-centered strength/momentum model**, **not** the proprietary Relative Rotation Graph (RRG) methodology. Let:

- `P(s,t)` = adjusted close of sector ETF `s` on trading session `t`.
- `P(SPY,t)` = SPY adjusted close on the same session.
- `Q(s,t) = P(s,t) / P(SPY,t)` = sector-to-SPY price ratio.
- `L` = sessions selected by **RELATIVE TIME**.
- `M = max(2, floor(L / 2))` = momentum comparison lag, in sessions.

**Relative strength (horizontal axis, %):**

`RS(s,t) = 100 × [ Q(s,t) / Q(s,t−L) − 1 ]`

**Relative strength momentum (vertical axis, percentage points):**

`MOM(s,t) = RS(s,t) − RS(s,t−M)`

Here `t−L` and `t−M` mean earlier **trading observations**, not calendar-day subtraction. The ratio compares adjusted-price performance over the lookback; the momentum metric measures how that lookback-relative-strength value changed over `M` observations. Momentum is measured in **percentage points (pp)**, not percent change of RS.

### Quadrant classification

| Quadrant | Condition | Meaning |
|---|---|---|
| **Leading** | `RS ≥ 0` and `MOM ≥ 0` | Outperforming SPY over the RS lookback, with non-declining RS |
| **Improving** | `RS < 0` and `MOM ≥ 0` | Underperforming SPY over the RS lookback, but RS is improving |
| **Weakening** | `RS ≥ 0` and `MOM < 0` | Outperforming SPY over the RS lookback, but RS is deteriorating |
| **Lagging** | `RS < 0` and `MOM < 0` | Underperforming SPY over the RS lookback, with declining RS |

**Zero belongs to the nonnegative side** of each threshold. The quadrant is determined from the latest available trading session inside To Date, using the selected Relative Time. The four KPI cards count how many selected sectors are classified in each quadrant.

### Rotation paths and visual interpretation

Each point is the sector's current `(RS, MOM)` pair. The chosen movement path connects up to the selected number of **daily historical indicator observations** ending at the as-of date. The path is drawn using a **Plotly spline** (`smoothing = 0.65`) to look continuous. The curve between observations is **visual interpolation only**: it does not represent additional measured prices or alter calculations. A hollow circle marks the path's first observation and an arrow indicates the most recent direction. Paths can bend, loop or cross themselves. Showing only one path at a time avoids cross-sector trail clutter but does **not** guarantee the path never crosses itself or an endpoint.

The map is a **relative** diagnostic: Leading does not necessarily mean positive absolute returns, and Lagging does not necessarily mean negative absolute returns.

## 4. Sector performance chart and classification table

Let `t0` be the **first** available trading session inside From/To and `t1` the **last**. Both returns are computed from adjusted closing prices:

`SectorReturn(s) = 100 × [ P(s,t1) / P(s,t0) − 1 ]`

`SPYReturn = 100 × [ P(SPY,t1) / P(SPY,t0) − 1 ]`

`Excess(s) = SectorReturn(s) − SPYReturn` **(percentage points)**

The **horizontal bar chart** ranks sector excess returns from the selected period, with a vertical zero reference line. Positive bars outperform SPY over that period; negative bars underperform. Bar color reflects the sector's **quadrant**, which is calculated over the separate Relative Time lookback and may not agree with the sign of the selected-period excess return.

The **classification table** displays ETF, sector, quadrant, RS (%), RS momentum (pp), selected-period sector return (%) and selected-period excess vs SPY (pp). It is sorted by relative strength descending by default and can be interactively sorted.

## 5. Sector trends vs SPY: every line starts at zero

For each trading session `t` in the selected period, using the **same initial date `t0`** for sector and SPY:

`CumulativeSector(s,t) = 100 × [ P(s,t) / P(s,t0) − 1 ]`

`CumulativeSPY(t) = 100 × [ P(SPY,t) / P(SPY,t0) − 1 ]`

`Trend(s,t) = CumulativeSector(s,t) − CumulativeSPY(t)` **(percentage points)**

At `t = t0`, both cumulative returns equal zero, so **every sector trend starts at exactly 0 pp**. For example, if a sector has returned **+8%** and SPY **+5%** since the selected starting session, its plotted value is **+3 pp**. If the sector is **−4%** and SPY **−2%**, its plotted value is **−2 pp**.

- **Above 0:** The sector has outperformed SPY cumulatively since the selected start.
- **Below 0:** The sector has underperformed SPY cumulatively since the selected start.
- **Rising/falling:** Its cumulative performance gap versus SPY is increasing/decreasing. A rising line does not necessarily imply a rising sector price.

This chart plots **cumulative-return differences**, not daily excess returns and not the sector/SPY ratio. It uses the **From/To** dates, not the Relative Time lookback. Trend lines are straight connections between actual daily observations; they are not smoothed or forecast.

## 6. Validation, freshness and missing data

The dashboard downloads all 11 sector ETFs **plus SPY** and validates the primary-source data before showing classifications. It checks for:

- Missing ETF or benchmark data, required Open/High/Low/Close/Adj Close/Volume columns, nulls, duplicate dates and nonpositive prices or negative volume.
- Impossible OHLC ordering (for example, High below Open/Close/Low).
- Missing benchmark-aligned sessions *within each ETF's available span*, or an ETF lacking the latest SPY session.
- Adjusted-close daily changes greater than **15%**, flagged for review as **warnings**, not automatic failures.
- Stale data (a warning when a recent end date was requested but the last observed session is more than five calendar days before it).

**FAIL:** Critical integrity errors; classifications are withheld. **WARNING:** Data is usable but flagged issues are displayed. **PASS:** The listed primary-source checks passed. PASS does **not** mean prices were independently cross-checked or audited. Validation is not a guarantee of complete market-data accuracy.

Missing values are **not forward-filled** in the trend series. An invalid or unavailable starting sector price prevents a zero-based trend for that selection. The latest session can lag the current day, especially before market close, on weekends and holidays.

## 7. Refreshing, scheduled checks and architecture

- **On-demand dashboard:** Streamlit retrieves market data through `yfinance`. Its price-download cache lasts **3,600 seconds (one hour)**. Opening or rerunning the app after cache expiry fetches again; an already-open idle browser is **not** guaranteed to refresh itself automatically.
- **Manual refresh:** The **Refresh now** button clears that cache and reruns the app.
- **Scheduled GitHub Actions check:** `.github/workflows/daily-data-check.yml` runs at **23:30 UTC Monday–Friday** (6:30 p.m. Eastern Standard Time / 7:30 p.m. Eastern Daylight Time), subject to GitHub scheduling delays and skips. The workflow calls `daily_check.py`, checks approximately **45 calendar days** of recent data and uploads `data_quality_report.json` as a workflow artifact.
- **No database:** The workflow **does not** persist historical price data, commit reports to the repository, or push updates into a running Streamlit session. The dashboard downloads its own prices when needed. GitHub Actions may be run manually, but manual daily execution is not required for normal dashboard use.

### Files in the repository

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI, controls, KPI cards, plots and wiki navigation |
| `market_data.py` | Yahoo download, validation, relative rotation calculations and zero-based trend |
| `daily_check.py` | Standalone data-quality verification and JSON report |
| `.github/workflows/daily-data-check.yml` | Scheduled and manually dispatched verification workflow |
| `tests/` | Synthetic-data tests for market calculations |
| `requirements.txt` | Python dependencies |
| `README.md` | Installation and deployment instructions |
| `WIKI.md` | This documentation, displayed inside the application |

## 8. Important limitations

1. **Historical classifications are not predictions.** Sector rotation can change quickly; relative outperformance does not guarantee a positive return.
2. **SPY is a proxy** for the S&P 500, not the index itself; sector ETFs have their own fees, holdings and tracking differences.
3. **The quadrant model is custom**, not the proprietary JdK RRG method. Its axes and quadrant names should not be treated as directly interchangeable with commercial RRG charts.
4. **Lookback and display window are different concepts.** The rotation map and period-excess chart can show different signs without a calculation error.
5. **Smooth paths are cosmetic**, and intermediate positions on the spline are not observed data.
6. **Provider dependence:** There is no second-source verification, and Yahoo Finance may revise or delay prices.
7. **No database or continuous streaming:** Data is downloaded on demand; scheduled validation does not update an open dashboard.
8. **Date and data availability:** ETF inception dates, holidays, incomplete sessions and missing provider records can restrict historical comparisons.

**Glossary:** **Adjusted close** = provider-adjusted closing price; **RS** = relative strength over the chosen lookback; **MOM** = change in RS over a shorter lag; **pp** = percentage points; **as-of date** = last observed trading session inside the chosen date range; **excess return** = sector cumulative return minus SPY cumulative return.
