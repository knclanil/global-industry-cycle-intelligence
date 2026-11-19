# Global Industry Cycle Intelligence

## NEW: India Sector & Factor Holdings (Constituent Explorer)

Under **Factor Analysis → India Sector & Factor Holdings**, explore the 31 NSE sector, thematic and factor constituent indices supplied for this project. The page consolidates securities by verified ISIN where possible, preserves every original index membership, shows factor-family versus parent-universe matrices, sector/factor overlaps, source-level diagnostic coverage, and CSV exports. **No ranking, absence penalties, or guessed weights are calculated.**

The page reads committed snapshots rather than downloading NSE files in Streamlit. To populate the initially empty data, run **Actions → India NSE Constituents Refresh → Run workflow**. For NSE 403 downloads, commit the original constituent CSV under `data/india_holdings/manual/` and rerun the job. See [`INDIA_CONSTITUENTS_GUIDE.md`](INDIA_CONSTITUENTS_GUIDE.md) and [`data/india_holdings/README.md`](data/india_holdings/README.md).

**New: India Holdings Changes** — The same page includes an observed changes tab with
index-by-index additions/removals, verified weight changes, symbol changes,
immutable snapshot history, a source index constituent-count trend, and
historical snapshot comparison. The first valid snapshot is the baseline;
no historical changes are invented. Scheduled NSE retrieval is handled by
GitHub Actions. See `INDIA_CONSTITUENTS_GUIDE.md` for safeguards and data files.

**Safe upgrades:** The release archive deliberately excludes generated
`data/india_holdings/*.csv`/`*.json` so copying it into an existing repository
cannot replace collected NSE records with empty placeholders. Preserve all
current `data/india_holdings/snapshots/`, `snapshot_meta/`, `manual/`, and
`history/` files. The first scheduled refresh after upgrade migrates older
snapshots into the history system automatically.



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


## Data Table — raw observations

The **Data Table** sidebar page shows source-returned daily OHLCV and adjusted-close observations for all ten dashboards, with symbol and date filters, source labels, coverage and missing-series reports, duplicate/invalid-price flags, validation messages, and downloadable CSV exports. A refresh button clears the shared one-hour market-data cache. No database or price filling is used. Source libraries may clean some data before the page receives it; validation is not independent provider verification.

### India government-bond fallback and Data Table provenance
India Asset Flow uses logical key `NIFTY_GSEC_10Y` for government bonds. It attempts an NSE 10-year benchmark G-Sec index via NSEPythonServer, then direct NSE history; if unavailable, it uses `SETF10GILT.NS` only when Yahoo returns valid history. No index/ETF stitching or forward-fill occurs. Check Data Table → India Asset Flow for source, instrument type, return basis, fallback flag, and underlying symbol. NSE index **price returns** and ETF **adjusted-close returns** are not identical methodologies. Live NSE availability is not guaranteed.

## Worked calculation examples in the Wiki

Open **Wiki** in the application and select any dashboard. Every dashboard's Wiki now includes a step-by-step numerical walkthrough of relative price ratio, relative strength, momentum, quadrant classification, selected-period excess return, and zero-based trends. Asset Flow pages additionally explain the Market Regime heuristic and the difference between price rotation and verified fund flows. These are illustrative calculations, not live data.



## Global Capital Intelligence Network (new first page)

A full-width, interactive Plotly relationship network with Country → Assets → Sectors and Global Assets → Equity → Global/USA/India Factors → Companies views. The page retains relative-time and date-range slicers, supports top-N, depth filtering, zoom/pan, node selection and a detail panel. Market nodes reuse the existing validated adjusted-price rotation calculations; the new 0–100 network score is a **within-layer percentile** (60% relative-strength percentile, 40% RS-momentum percentile). Scores across different universes are not directly comparable.

**Coverage boundaries:** Country-level asset and sector layers currently exist only for USA and India. Country → sector → company requires sector constituents and is intentionally not shown without them. Factor → company edges require user-uploaded holdings (CSV/XLSX, columns `factor,company,weight`, optionally `ticker,isin,as_of,source`); no fake holdings are supplied. Network edges represent membership/relationships and price-rotation proxies, **not measured fund flows**. The visual is a structured graph, not a physics-simulated neural network; click nodes to inspect connections. Data downloads require internet access when deployed. A live Streamlit Cloud rendering check has not been performed.


## Organic capital network (reference-inspired)

The first page now displays country and asset-class branches **together** in a radial, curved-edge network. There is no exploration-path selector. Retained slicers: Relative Time, From/To dates, and Top N. Factor-market filters and optional verified constituent uploads are under Network filters. Node selection opens a detail drawer below the graph. Node connections denote market relationships, **not actual measured fund flows**.

### Global Capital Intelligence Network: country-first parallel equity branches

The network now uses one hierarchy, without an exploration-path selector:
**GLOBAL → Country → ASSETS → Equity → SECTORS and FACTORS (parallel) → Companies**.
Sectors are positioned to the left of Equity and factors to the right. Non-equity assets appear as sibling asset nodes and do not incorrectly connect to equity factors. Country-specific asset, sector, and factor coverage is currently available for USA and India; other country nodes stop at the country level rather than inventing unsupported asset breakdowns. Factor-company connections appear only from uploaded constituent weights; sector-company links require independently verified sector constituents and are not fabricated. Network scores represent price-relative leadership, not measured fund flows.

### Network hierarchy (country-first, parallel sectors/factors)

The top intelligence page uses **GLOBAL → Country → ASSETS → Equity → SECTORS | FACTORS → Companies**. The sector and factor columns are separate, parallel children of each country's equity node. USA and India have supported country-specific datasets; other countries stop at their country node rather than being assigned unsupported asset/factor proxies. Global factor ETFs are not incorrectly placed beneath a country. Factor-to-company links require uploaded verified constituent holdings, and sector-to-company links are not shown without sector constituents. The graph depicts price-based market rotation and holdings relationships, **not measured money flows**.

## Galaxy network update (November 2026)

The first dashboard page now displays a bilateral **Global Capital Intelligence Galaxy**:

- **Left:** Global → Global Assets → Equity → Global Factors → constituent companies (when verified holdings are uploaded). Other global asset classes are separate satellites.
- **Right:** Global → Countries → country Assets → Equity → **Sectors and Factors in parallel** → companies (only when validated holdings are supplied).
- Country-specific equity/sector/factor branches currently rely on USA and India data. Other countries are displayed only to the depth supported by available feeds.
- Planet diameters are based on a square-root scaling of the peer-relative **Network Score** (0–100). Structural nodes without a score use a fixed neutral size; the Global root has a fixed size. Quadrant colors are unchanged.
- Curved connections represent hierarchy or verified holdings relationships, **not measured money flows**. Company connections require uploaded holdings. Missing holdings are not fabricated.
- Existing Relative Time, date-range, Top N and holdings upload controls remain available. The layout supports Plotly pan and zoom, with a selected-node detail view.

This is a deterministic orbital/galaxy layout, not a physical gravity simulation. It does not include continuous animation or guaranteed collision-free labeling at very large Top N values.

### Midnight Cosmos visual refresh (November 2026)
The Capital Intelligence Galaxy uses a near-black navy canvas, faint seeded stars, curved low-contrast connections, and layered glowing planet markers. Planet diameter represents a peer-relative score; original quadrant colors and the Global Assets / Country Assets hierarchy remain unchanged. Structural nodes use a fixed size. Click a planet to highlight its immediate neighbors. This is a visual redesign, not a change to market data or a claim of measured capital flows.

## Persistent nightly incremental refresh

The workflow `.github/workflows/nightly-market-refresh.yml` runs after NSE and US market closes, stores per-symbol Parquet snapshots in `data/market/`, and commits changed snapshots to the repository. India runs at 18:00 IST weekdays; US-listed global/USA data runs at 00:30 UTC Tuesday–Saturday (19:30 EST / 20:30 EDT). GitHub scheduled workflows may be delayed. Holidays result in no new session, not fabricated prices.

**Initial setup:** enable GitHub Actions with read/write workflow permissions (`Settings → Actions → General → Workflow permissions → Read and write permissions`), then open `Actions → Incremental market data refresh → Run workflow → all`. The workflow's default branch must be the deployment branch. The initial historical bootstrap downloads five years; subsequent refreshes request a 10-calendar-day overlap and replace revised dates. On provider failure existing snapshots remain untouched; see `data/market/refresh_*.json` and workflow logs.

The dashboard loads committed snapshots rather than fetching live prices on normal interactions; until the first bootstrap it falls back to existing live downloads for continuity. `st.cache_data` still caches loaded frames for one hour; a redeploy or cache expiry loads new commits. Price-provider redistribution terms should be checked before using a public repository. This workflow stores prices, **not precomputed RS/momentum scores**, which remain date-range-dependent.


## USA Company Holdings Leadership
The **USA Company Holdings Leadership** page and [methodology wiki](HOLDINGS_LEADERSHIP_WIKI.md) rank verified issuer holdings across 7 factor and 11 sector iShares portfolios. A separate [GitHub Actions workflow](.github/workflows/holdings-refresh.yml) attempts automatic verified refresh. Upstream files must expose verifiable as-of dates; failed sources never trigger false removals.


### Additional iShares holdings sources and refresh parser
Ten additional source IDs are tracked in `data/holdings/pending_sources.json` pending factor/sector classification. The holdings refresh parser now recognizes iShares CSV/Excel holdings-date preambles; verify against live documents before treating the pipeline as production-ready. See `HOLDINGS_LEADERSHIP_WIKI.md`.

---

## India Company Financial KPIs + Sector/Factor Financial Analysis (2026-11)

Two **additional** India pages are available (USA Company Financial Research and Company Financial KPIs remain unchanged):

- **Global Intelligence → India Company Financial KPIs**: one-company annual/quarterly Yahoo Finance research, returns and balance-sheet KPIs, asset per-share / Graham screens, hypothetical cash-flow intrinsic value and liquidation scenarios, official NSE holdings membership and independent Screener consolidated links.
- **Factor Analysis → India Sector & Factor Financials**: NSE-verified sector/index membership with **unweighted** group financial KPI medians, factor-family deduplication, company drilldowns, sector × factor heatmap and provider coverage.

The original **India Sector & Factor Holdings** continues collecting/tracking 31 NSE constituent CSV sources. To populate the financial pages, first run **India NSE Constituents Refresh**, then **India Company Financials Refresh** in GitHub Actions. The latter processes 25 symbols per batch by default. These financial pages make no external requests while loading; they read persisted snapshots. **No ranking function or inferred holding weights** are included.

Read **[`INDIA_FINANCIAL_ANALYSIS_GUIDE.md`](INDIA_FINANCIAL_ANALYSIS_GUIDE.md)** before deploying to a public app: Yahoo Finance/yfinance and Screener.in have data-access and redistribution restrictions, and their data must not be republished without appropriate rights. Screener pages are linked only; they are not scraped.
