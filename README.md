# USA financial collection, storage and fundamental rankings

This update extends (and **does not replace**) the existing USA SEC+quote collection workflow. It produces a separately auditable **fundamental ranking dataset** from existing verified USA memberships and locally cached official SEC CompanyFacts. It is intentionally **not a StockAnalysis, Finviz, or Yahoo Finance HTML scraper**.

## Sources and permissions

- **SEC** — automated collection already performed by `scripts/refresh_usa_company_fundamentals.py` under `SEC_USER_AGENT`. The new ranking script reads the cached raw CompanyFacts without making a network request.
- **Yahoo** — this update reads **existing** `data/usa_research/quotes.csv` from the current pipeline for a dated USD market-capitalization tiebreak. It does not add new Yahoo webpage scraping.
- **StockAnalysis.com** — verified reference URLs are generated for every ticker. Its terms prohibit automated bulk collection and it does not offer a public API; these are **manual research links only**.
- **Finviz** — reference URL is generated per ticker. It is **not scraped**.

Automated ingestion from the latter two websites would need appropriate permission or licensed data-access arrangements. A link is **not** evidence that a metric was collected from that site. This package never mislabels a SEC number as a Finviz/StockAnalysis/Yahoo value.

## What gets saved

All under `data/usa_research/`, auto-published using the existing workflow's clean-worktree publishing step:

1. `fundamental_rankings.csv`: one row per verified USA issuer with ticker, name, sector/factor membership, ROE (%), current ratio, operating margin (%), net margin (%), diluted EPS growth (%), raw financial values, per-metric ranks, rank sum, optional market-cap tiebreak and final rank.
2. `fundamental_field_evidence.csv`: **per-field** original SEC concept, value, fiscal period end, filing date, accession number, source; dated quote provenance where available.
3. `financial_source_links.csv`: all ten supplied StockAnalysis/Finviz/Yahoo reference URLs with `TICKER` replaced per company.
4. `fundamental_ranking_report.json`: metric coverage, ranked/unranked counts and diagnostic sampling.

## Ranking logic

1. Among companies with **all five usable metrics**, rank ROE, Current Ratio, Operating Margin, Net Margin, and diluted EPS year-on-year growth, with high values ranking best.
2. Sum five individual ranks; **smallest sum is best**.
3. **Market cap only breaks ties in rank sum**; it is never added to fundamental rank sum. Highest known USD market cap wins. Equal or unavailable cap can leave a shared final rank.
4. Missing metrics yield **unranked**, never 0 or an invented rank.
5. For EPS growth, a positive prior-year EPS base and positive current EPS are required; loss-to-profit transitions need a different signal.
6. Banks, insurers, REITs and other financial institutions are excluded from the five-metric general-company model because Current Ratio/margins have different meanings. They remain in the exported universe marked unranked. A specialized model can be added later.
7. Only annual, filed SEC CompanyFacts are used. The evidence file retains periods and facts. The script rejects materially misaligned or stale observations.

**Interpretation:** These are *fundamental ranking numbers*, not valuation, investment suitability, or backtested predictions. Very high current ratios may be economically less favorable; the simple ordering follows the requested ranking convention.

## Install using GitHub Desktop

1. Extract this ZIP.
2. Open your existing repository (`global-industry-cycle-intelligence`) in GitHub Desktop, then **Repository → Show in Explorer**.
3. Copy **`scripts/build_usa_fundamental_rankings.py`** and **`tests/test_usa_fundamental_rankings.py`** into matching repo subfolders.
4. Copy the supplied complete **`.github/workflows/usa-company-fundamentals-refresh.yml`** into the matching folder, replacing its previous version. This is the existing USA automatic pipeline with a new build step added immediately before publishing. **Do not overwrite a more recent customized workflow without reviewing the diff.**
5. Commit and **Push origin**. The normal weekday USA workflow will generate the new files on its next successful run. You can also run the existing USA Company Fundamentals and Valuations Refresh workflow manually once.
6. Ensure the existing `SEC_USER_AGENT` secret remains set. No new API keys are required.

For a local rebuild from already cached data:

```bash
python scripts/build_usa_fundamental_rankings.py
```

Tests:

```bash
python -m unittest discover -s tests -p 'test_usa_fundamental_rankings.py' -v
```

## Compatibility and limits

This is a **data backend addition**. It does not hide/add USA pages or overwrite the Knowledge Graph, India, or Streamlit app. To visualize the new ranks, a subsequent USA Financial KPIs UI change can read `data/usa_research/fundamental_rankings.csv`. Unlike past patches, this package is not claimed to have fetched or populated your live financial values: it was validated offline only.

The number of companies that receive a complete five-metric rank depends on cached SEC fact coverage. The source HTML websites are not bulk-ingested; that's deliberately disclosed rather than pretending they provide an unrestricted free data feed.
