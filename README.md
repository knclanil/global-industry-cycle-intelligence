# USA-first fundamentals and valuation coverage trial

## Purpose
Keep India unchanged. Enrich **verified USA ETF issuers only** using Yahoo historical close and available Yahoo price/valuation metadata. Reuse the existing SEC financial summaries. Missing valuations remain null. The pilot is deliberately manual and small before scaling.

## Install
Copy `.github/workflows/usa-quote-coverage-pilot.yml`, `scripts/usa_quote_coverage_pilot.py`, and `tests/test_usa_quote_coverage_pilot.py` into the matching folders of the main repository. Commit and push via GitHub Desktop. Do not replace existing USA/India financial workflows or the Streamlit `app.py`.

## Run
GitHub Actions → **USA Quote and Valuation Coverage Pilot** → Run workflow.
- First trial: `tickers=AAPL,MSFT` and `limit=2` (only if both are verified ETF holdings).
- Next trial: blank tickers, `limit=25`; prioritizes existing SEC `fundamental_ready=Yes` companies and skips quotes younger than 7 days.

## Output
- `data/usa_research/quotes.csv` (dated prices and available Yahoo P/E, P/B, market cap)
- `data/usa_research/quote_pilot_report.json` (fetched/failed/price/valuation coverage)
- `data/usa_research/company_research.csv` (existing SEC + quote integration)
- `data/research_coverage/fundamental_coverage.json` (both-market readout; India untouched)

**How to assess:** A green workflow only demonstrates it executed. Compare `USA.metrics.price`, `.pe`, `.pb`, `USA.readiness.valuation_ready` and `USA.readiness.research_ready` in the refreshed coverage file. Missing P/E and P/B can be legitimate for companies with losses or Yahoo missing metadata. Do not manufacture these numbers.

**Boundaries:** Yahoo Finance is unofficial and may throttle. Market prices can be delayed. `quote_asof` represents fetch time; `quote_source` includes the exchange trade date. The trial does not create composite scores, alter India, or modify Knowledge Graph. Existing `build_usa_research.py` freshness/peer validation rules still apply. Only publish after confirming acceptable use of provider data in a public repository.
