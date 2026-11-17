# Global Industry Cycle Intelligence Dashboard & Economic Wiki Knowledge Center

A **standalone** Streamlit application for India–USA–Global sector comparisons, market-cycle exploration, relative-strength rankings, an early-recovery scanner and a source-linked economic/industry research library. **No database. No versioning files.**

## Quick start

1. Create a **new GitHub repository** and upload this project's contents to its root. Do not upload into the Factor Holdings Intelligence repository.
2. Open **Actions → Refresh market data and publisher feed → Run workflow**. The workflow downloads available history, calculates monthly market-cycle signals and discovers RSS metadata. Initial full history may take several minutes.
3. Deploy the repository to Streamlit Community Cloud with `app.py` as the entry point, or run locally with:

   ```bash
   pip install -r requirements.txt
   python scripts/collect_prices.py
   python scripts/analyze.py
   python scripts/monitor_publishers.py
   streamlit run app.py
   ```

4. Use **Data & Methodology** to inspect missing or mismatched sector instruments. Modify `config/instruments.csv` when a Yahoo ticker is unavailable, then rerun the workflow.
5. Add only publisher-verified RSS/Atom URLs to `config/publishers.json`. Homepage-only entries are research links, not monitored feeds.

## Application pages

1. Cycle Overview — three-market stage matrix, relative-return heatmap, monthly transitions.
2. Cycle Explorer — historical normalized sector vs benchmark prices, relative strength and monthly stage history.
3. Cross-Market Comparison — India/USA/Global sector comparisons and approximate local-currency performance.
4. Leadership & Rotation — sortable sector rankings, quadrant scatter and performance charts.
5. Opportunity Scanner — rule-based early recovery, leadership, weakening and laggard filters, CSV export.
6. Knowledge Center — feed, country wiki, industry wiki, opportunity radar, publisher library, archive, methods and source status.

## Data and sourcing

- Market history: unofficial Yahoo Finance access through `yfinance`. **Not guaranteed**; some Indian symbols may not resolve.
- `data/prices.parquet` — daily adjusted close; `sector_snapshot.parquet` — latest monthly indicators; `sector_history.parquet` — monthly cycle classifications.
- `data/publications.json` — source-linked metadata from RSS feeds; no scraped full reports, fabricated AI summaries or investment conclusions.
- `knowledge/` — editable Markdown wiki.
- `config/instruments.csv` — transparent index/ETF proxy mappings and caveats.
- GitHub Actions runs at 23:25 UTC Monday–Friday; individual source failures are tolerated and logged.

## Important limitations

**Market cycle is not the same as an industry fundamental cycle.** The stage classifier only uses benchmark-relative sector prices. No earnings, production, economic indicators, fund flows, automatic report summarization, verified investment opportunities, USD FX conversion, or formal lead–lag statistical tests are implemented yet. These require separate validated sources and should not be inferred from the current market signals. Historical coverage is limited by each instrument's availability.

This package is a functional, database-free foundation, **not a claim that every discussed advanced data source or fundamental research feature is operational**. The wiki includes editable pages and a source registry; only the explicitly configured RSS feeds are automatically monitored.


## NSE India sector tracking

The **NSE India Sectors** page displays the official NSE index snapshot when the NSE permits automated access. Run `python scripts/collect_nse_indices.py` or the GitHub Actions refresh workflow. A configurable list is in `config/nse_indices.csv`. `data/nse_collection_status.json` reports any access errors. The snapshot is **not** a historical index series and the list is **not** a verified complete export of the live page. Do not interpret missing rows as zero returns. NSE usage restrictions and anti-bot measures may prevent unattended access.

## NSE historical data (official source)

Use **Actions → Backfill NSE historical index prices → Run workflow** to request up to 20 years of index history. This is a one-time backfill; the standard refresh updates recent observations. Historical data appears in **NSE India Sectors** with charts, returns, relative strength versus NIFTY 50, coverage diagnostics and CSV download.

NSE may reject automated requests (401/403/429). The collector does not bypass access controls, and it never invents prices. If blocked, use the official NSE historical index download interface and put its CSV files in `imports/nse/`, named after the index (e.g. `NIFTY IT.csv`). Commit these files and run `python scripts/collect_nse_history.py --mode import`. Data is stored in `data/nse_index_history.parquet` and `data/nse_history_coverage.json`. Verify applicable NSE data use and redistribution terms.

Index history may be shorter than 20 years, especially for newer indices. These are price-index closes, not TRI. The historical page is separate from the global proxy-based market-cycle classifier.
