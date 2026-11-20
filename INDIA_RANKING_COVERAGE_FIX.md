# India Fundamental Quality — blank page correction

## Diagnosis
The original quality-ranking loader read only `data/india_financials/companies/*.json`, which are Yahoo *annual statement* snapshots. The shipped folder had no company JSON records, even though the supplied Factor Holdings Intelligence reference project contained `data/india_fundamentals/latest.csv` with 514 Indian ticker-level ratio snapshots. Thus the India quality page was empty.

## Fix
- Bundled the reference project's `latest.csv` (from the user-provided archive) as `data/india_financials/reference_snapshot.csv`.
- Display one row per reference ticker when there is no saved multi-year annual-statement record for that ticker.
- If a proper annual statement record exists, it takes precedence; source types are never silently merged.
- Show incomplete financial coverage by default when there are no rank-eligible companies, rather than showing a blank ranking.
- Keep single-period ratios strictly **unranked**: three consecutive annual statement years are still required for the Fundamental Quality & Consistency score.
- Do **not** compute statement-derived EPS, Graham, DCF or consistency from a one-period ratio snapshot. Those remain missing until underlying annual statements and shares are saved.

## Data freshness and limitations
The bundled reference snapshot reflects the date stored in its rows (most from 2026-11-19), not live quotes. Columns were obtained in the earlier attached reference project via NSE/Yahoo and may require fresh verification before investment use. Provider ratios are reference data, not recalculated from consolidated financial statements.

## Getting ranked Indian companies
Run the existing `India Company Financials Refresh` job and make sure annual statement JSON files with at least three consecutive fiscal years are committed under `data/india_financials/companies/`. Check data-source coverage before assessing rankings. This fix **does not** attempt to scrape Screener in Streamlit or fabricate historical series.
