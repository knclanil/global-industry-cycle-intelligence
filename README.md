# India Investment Research — two integrated pages

This patch adds two India sidebar pages after **India Asset Flow → India Sector → India Factors**:

1. **Investment Opportunity Screener** — one row per verified company, sector/factor/source-index multi-select filters with ANY or ALL *within each category*, search, data-readiness gates, transparent scores (when available), CSV export.
2. **Company Deep Dive** — company selection from screener, sector/factor/index evidence, cached financials, valuation indicators, peer comparison, source dates, coverage gaps, independent company reference.

The original India assets, sector, factors, Knowledge Graph, membership table and financial collection workflows are **not modified**. The old duplicate research pages remain hidden, not deleted.

## Install (GitHub Desktop)

1. Extract this ZIP and open your repository via GitHub Desktop → Repository → Show in Explorer.
2. Copy **india_research_data.py**, **india_opportunity_ui.py**, and **india_company_deep_dive_ui.py** to the **root** of the repository.
3. Copy `scripts/install_india_research_pages.py` to `scripts/`.
4. Ensure that `scripts/build_india_opportunity_dataset.py` exists. If not, copy the supplied version from `scripts/`. It is the dataset builder from the prior financial pipeline package.
5. Open **Repository → Open in Terminal**, then run:

   ```bash
   python scripts/install_india_research_pages.py
   ```

   The installer only updates `app.py` navigation and routing. It is idempotent and refuses to edit an unexpected sidebar layout. If it refuses, do **not** overwrite your latest `app.py` blindly; review the differences with the included `app.py` reference and adapt the two navigation entries.
6. Commit and push changes with GitHub Desktop. Streamlit Cloud will redeploy.

### Optional alternate install

The included `app.py` is a **complete reference** derived from the previously delivered India navigation cleanup package, with the two new entries added. You may copy it directly **only if** it matches your latest app changes. Otherwise use the installer to preserve subsequent edits.

## Data prerequisites

The pages read `data/india_financials/opportunity_research.csv`, created by the existing automated financial pipeline. When that file is missing, the pages build an **in-memory, read-only** view from:

- `data/india_holdings/companies.csv`
- `data/india_holdings/constituents.csv`
- `data/india_financials/company_financial_summary.csv` (optional, missing financials show N/A)

No Yahoo Finance/NSE requests occur on page load. The company universe is available even when financial values are missing, provided the verified holdings dataset exists. This patch does not increase financial-data coverage and **does not** validate investment predictions.

## Correctness/limitations

- Cross-category filters combine with AND; within a filter's selected items ANY/ALL is user-selectable.
- Scoring only uses existing cached comparable KPIs; missing scores remain blank rather than zero.
- Financial values can have unverified standalone-vs-consolidated scope or unspecified units. No inferred weights or rotation quadrants are introduced.
- Sector memberships are **verified NSE sector-index labels**, not necessarily the same canonical sector categories as the Knowledge Graph. They are not automatically equated.
- This provides a usable research interface, not yet a backtested end-to-end model of asset → sector → factor rotations. The Assets/Sector/Factor pages themselves are preserved.

## Tests

Run `python -m unittest discover -s tests -p test_india_research_pages.py -v`.

These targeted tests cover ANY/ALL filtering, cross-category matching, readiness, score display, and idempotent navigation patching. No live Streamlit or GitHub Actions deployment has been executed in this environment.
