# Global Industry Cycle Intelligence

## Pages
- **USA Sector** — 11 US sector ETFs versus SPY.
- **India Sector** — 12 Indian sector index symbols versus Nifty 50 (`^NSEI`).
- **Wiki** — methodology for each market, with a market selector.

Both sector pages use the same controls, KPIs, relative rotation map, sector performance bars, zero-based relative trend chart, and classification table. The India series use Yahoo Finance NSE index tickers. Availability varies by symbol and provider; missing indices are warned about and omitted, not fabricated. No database.

Run: `pip install -r requirements.txt` then `streamlit run app.py`.

The scheduled GitHub Action checks **USA** data only; India data is downloaded when its page loads or Refresh now is pressed.

# Global Industry Cycle Intelligence

A **USA sector rotation** dashboard designed for **GitHub + Streamlit Community Cloud**. No database, no API keys required for the initial Yahoo Finance feed.

## Features

- 11 US sector ETFs, SPY benchmark
- Select All / single / multi-sector slicer
- Relative Time: 1W, 2W, 4W, 1M, 3M, 6M, 12M
- From Date / To Date historical slicer
- Four KPI cards: Leading, Improving, Weakening, Lagging
- Interactive relative rotation map with historical trails
- Sector excess-performance bar chart and sortable classification table
- Data integrity checks and explicit primary-source verification status
- Refresh Now button, one-hour data cache, scheduled GitHub Actions data-quality checks

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
