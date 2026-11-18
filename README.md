# Global Industry Cycle Intelligence

## Dashboard navigation (display order)

The live application includes **Global Factors** (ACWI), **USA Factors** (SPY), and **India Factors** (Nifty 50) alongside the sector and country dashboards. Each has the same rotation, performance, zero-based trend and classification visuals. See `GLOBAL_FACTORS_WIKI.md`, `USA_FACTORS_WIKI.md`, and `INDIA_FACTORS_WIKI.md`. India factors use NSE historical factor indices; Yahoo is a benchmark-only fallback, not an unverified factor-index replacement.


1. **Global Sectors** — 10 global sector ETFs compared with ACWI.
2. **USA Sector** — 11 US sector ETFs compared with SPY.
3. **India Sector** — Indian sector indices compared with Nifty 50 (`^NSEI`).
4. **Wiki** — methodology for all three markets, with the same Global → USA → India selector order.

Each market has the same sector/date slicers, four quadrant KPIs, relative rotation map, excess-performance bars, zero-based relative trend chart, and classification table. The app has no database.

## Data sourcing and validation at a glance

| Market | Primary | Fallback | Scheduled audit |
|---|---|---|---|
| Global | Yahoo Finance (`yfinance`) | None | Not currently scheduled |
| USA | Yahoo Finance (`yfinance`) | None | USA only, weekdays |
| India | NSE India endpoints | Yahoo Finance, per unavailable series | Not currently scheduled |

A dashboard PASS indicates **internal structural validation**, not zero missing observations, an exchange-calendar audit, or independent cross-provider price reconciliation. Market data is fetched on demand and cached for one hour; an idle open browser may not refresh automatically. See the in-app Wiki for detailed formulas, missing-series handling and limitations.

## Deploy to Streamlit

1. Push **the contents of this directory** to the `global-industry-cycle-intelligence` GitHub repository's `main` branch.
2. On Streamlit Community Cloud, select that repository and set the main file to `app.py`.
3. Deploy. No secrets or database are required.

Run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Run offline unit tests (synthetic price data):

```bash
python -m unittest discover -s tests -v
```

## Data refresh and schedule

Streamlit fetches data when opened, after its one-hour cache expires, or when **Refresh now** is pressed. GitHub Actions (`.github/workflows/daily-data-check.yml`) separately runs a market-data integrity check at **23:30 UTC, weekdays** and uploads `data_quality_report.json` as a workflow artifact. This does **not** push historical prices into GitHub, update an open browser automatically, or guarantee that Yahoo Finance has posted final end-of-day prices. Scheduled GitHub Actions may run late or be skipped; monitor Actions for failures. If a holiday falls on a weekday, the check evaluates the most recent available session. The workflow uses UTC, so its US Eastern time changes with daylight saving time.

## Classification definitions

For sector ETF adjusted-close price `S` and SPY adjusted-close `B`, define relative ratio `Q = S / B`. For chosen relative window `L` trading sessions, `RS = 100 × (Q / Q.shift(L) − 1)`. Let `M = max(2, floor(L/2))`; momentum `= RS − RS.shift(M)`. Positive RS and positive momentum = Leading; negative RS and positive momentum = Improving; positive RS and negative momentum = Weakening; negative RS and negative momentum = Lagging. Zero counts as positive. This is an original, transparent model, **not** the proprietary RRG calculation. Short lookbacks can be noisy.

Date Range controls the historical trail, absolute/excess returns, and as-of classification date. Relative Time controls the indicator window. Additional pre-range prices are fetched for warm-up. Sector excess return is sector adjusted-price return minus SPY adjusted-price return in percentage points.

## Data quality limitations

The current dashboard validates completeness against SPY, duplicates, OHLC relationships, nonpositive values, and flags unusually large adjusted-price moves. **Independent cross-provider verification and full corporate-action reconciliation are not implemented.** The status `PASS` therefore refers only to primary-source structural checks, not investment-grade verification. Yahoo Finance is an unofficial feed; it may throttle requests or revise historical data. The app does not persist market data or require a database. This is research software, not investment advice.

## Sector trends vs SPY

The dashboard includes a line chart for the selected sectors over the **From Date → To Date** range. Each line is normalized to **0 percentage points on the first trading session**. For each subsequent date, the plotted value is `100 × (sector_adjusted_close / sector_start_adjusted_close − SPY_adjusted_close / SPY_start_adjusted_close)`. Positive means cumulative outperformance versus SPY; negative means underperformance. This chart uses the date range slicer, not the Relative Time indicator window. It uses the same validated adjusted-price feed as the other visuals and does not interpolate missing values.

## Dashboard Wiki

Open the **Wiki** page using the app sidebar to read the complete calculation methodology, sector coverage, filter semantics, data-validation rules, refresh behavior, and limitations. The documentation is maintained in [`WIKI.md`](WIKI.md) and is available even when market-data retrieval fails.

### Wiki deployment troubleshooting

The Wiki normally reads `WIKI.md` from the same folder as `app.py`. Commit **both files** to the root of the deployed GitHub branch (not inside an extra nested folder). The application also includes a built-in documentation fallback, so the Wiki continues working if `WIKI.md` is missing. To edit documentation, update `WIKI.md` and commit it.

### India market-data source priority

India sector and Nifty 50 daily index prices are requested from NSE India historical index endpoints first. When an individual index cannot be retrieved, Yahoo Finance is used as a fallback for that index. The India dashboard identifies fallback series. Source availability is not the same as independent price reconciliation; the dashboard does not claim audited NSE/Yahoo agreement. NSE may restrict automated requests.


## Global Sectors

The **Global Sectors** navigation page uses ten global sector ETFs (IXN, IXG, IXJ, IXC, KXI, RXI, EXI, MXI, JXI, IXP) against **ACWI**. Yahoo Finance supplies adjusted daily prices. It shares the USA/India visual layout and relative-strength, momentum, excess-return and zero-start trend definitions. See `GLOBAL_WIKI.md`. The scheduled GitHub Action currently checks USA data only.


## Global Countries

The **Global Countries** page covers 20 US-listed country ETFs against ACWI with the same charts and controls. Its methodology is documented in `COUNTRIES_WIKI.md`.

### India historical index retrieval (NSEPythonServer)
`requirements.txt` installs `nsepythonserver` for hosted Streamlit. Both India Sector and India Factors first try the wrapper's `index_history` against Nifty Indices, then the existing NSE India endpoint, and finally verified Yahoo Finance fallbacks (India Factors: Nifty 50 benchmark only). Data is validated; missing factor indices are excluded, never fabricated. This integration has offline mocked tests but has **not** been verified against live NSE servers from this environment.

## Cross-asset rotation dashboards

Three new pages — **Global Asset Flow**, **USA Asset Flow**, and **India Asset Flow** — compare price-based cross-asset leadership with the existing rotation map, relative-performance bars, zero-based trends, classifications and a conservative market-regime heuristic. **These pages do not contain verified ETF net flows**, so "flow" is a descriptive page label rather than a measurement of actual investor subscriptions or redemptions.

- Global: ACWI benchmark, USD-listed equity, bond, credit, commodity, gold, REIT and cash ETF proxies.
- USA: SPY benchmark, USD-listed US equity, duration, credit, commodity, gold, REIT and T-bill ETF proxies.
- India: Nifty 50 benchmark (NSEPython/NSE primary, verified Yahoo ^NSEI fallback), India-listed equity, gold, silver, liquid and *availability-unverified* government bond ETF proxies. Coverage is incomplete for corporate bonds, broad commodities and REITs. Missing tickers are excluded, not fabricated.

See `GLOBAL_ASSET_WIKI.md`, `USA_ASSET_WIKI.md`, `INDIA_ASSET_WIKI.md` for definitions and caveats.
