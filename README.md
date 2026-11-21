# USA Research Workspace — matches the India research journey

Adds **USA Investment Opportunity Screener** and **USA Company Deep Dive** after USA Asset Flow, USA Sector, and USA Factors, without changing the existing graph, India pages, or company financial screens.

## Install (GitHub Desktop)

1. Extract the ZIP.
2. Copy `usa_research_data.py`, `usa_opportunity_ui.py`, and `usa_company_deep_dive_ui.py` into the repository root.
3. Copy `scripts/install_usa_research_pages.py` and `scripts/build_usa_research.py` into the repository `scripts` folder. Optionally copy the unit test into `tests`.
4. In **Repository → Open in Terminal**, run `python scripts/install_usa_research_pages.py`. This patches your existing `app.py` rather than replacing it. Run again safely if needed.
5. Commit and push from GitHub Desktop.

### Refresh cached SEC facts and the USA research summary

- Your existing **Verified iShares holdings refresh** must publish `data/holdings/latest_holdings.parquet`.
- Your existing **SEC fundamentals refresh** must publish the SEC company directory plus individual companyfacts JSON files in `data/fundamentals/` or `data/sec_cache/`.
- To generate a saved US research snapshot from already-cached SEC facts, run `python scripts/build_usa_research.py` from your repository root, then commit/push `data/usa_research/company_research.csv` and `data/usa_research/build_report.json`. This script makes **no HTTP requests**.
- If financial snapshot is not yet generated, the screener still shows your verified U.S. issuer memberships; financial values remain blank.

**USA pages**: USA Asset Flow → USA Sector → USA Factors → USA Investment Opportunity Screener → USA Company Deep Dive.

## Data integrity

- **Only USA** `sector` and `factor` iShares sources (not `global_sector` or `global_factor`) are eligible; only source rows explicitly locating issuer in the United States are included. This is narrower than “USA strategy funds contain multinational holdings.”
- One row per country-qualified issuer identity, not one row per ETF position.
- Source ETF memberships, factor families, sector families, source count and average weight preserved.
- Sector, factor and fund multiselect support ANY/ALL *within each group*, AND *across groups*.
- **No score is made up.** SEC facts provide annual fundamentals and growth, but raw SEC filings do not supply current stock quotes. P/E, P/B, price, quality/growth/valuation/research scores remain missing until a vetted quote, peer-comparison and scoring pipeline has been connected. This package does **not** claim to have valuation or opportunity scoring operational for the US.
- Company Deep Dive links to your already-existing `Company Financial Research` and `USA Company Financial KPI Intelligence` pages for more complete SEC-backed detail.
- The graph, existing Global/USA/India data and workflows are not modified.

## Local checks

`python -m unittest discover -s tests -p 'test_usa_research_pages.py' -v`

Python syntax and fixture tests were checked in the package build environment. No live Streamlit/GitHub workflow deployment was performed.
