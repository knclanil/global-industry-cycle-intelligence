# India Sector & Factor Holdings — Constituent Explorer

## Design

The new **India Sector & Factor Holdings** navigation item appears under Factor Analysis, while existing India Sector/Factor market-performance pages, Company Financial Research, Financial KPIs, and other features remain unchanged.

The page has five views:

1. **Company Directory** — one consolidated company per matched ISIN (or symbol-only provisional ID), searchable and filterable. Separate columns show factor families, exact factor/parent-universe memberships, sector indices, thematic indices, and strategy indices. Select a company to see its original source-index rows, ISIN, optional published weight, retrieval timestamp and official URL.
2. **Factor Membership Matrix** — each distinct factor family can be inspected across its Nifty 50/100/200/500 (or unspecified) constituent indices. Checkmarks mean observed membership; blank cells do **not** imply index eligibility.
3. **Sector & Factor Overlap** — explore each of the 15 sector/thematic constituent lists, the companies within it, and descriptive overlap *counts* with factor families.
4. **Source Index Browser** — all 31 NSE URLs, number of stored constituents, collection provenance, latest retrieval date and per-index holdings CSV exports.
5. **Data Coverage** — failed sources, missing snapshots, known source-weight coverage, identity-validation coverage and downloadable diagnostics.

No leadership ranking, cross-index absence penalties, hypothetical weights, or imputed cap designation are calculated.

## Dataset

**15 sector/thematic indices:** Media, PSU Bank, Bank, Financial Services, Pharma, IT, Realty, FMCG, Oil & Gas, Metal, Auto, Infrastructure, India Defence, Energy, India Manufacturing.

**16 factor/strategy indices:** Nifty500 Low Volatility 50, Nifty500 Momentum 50, Nifty500 Quality 50, Nifty500 Value 50, Nifty200 Momentum 30, Nifty200 Value 30, Nifty200 Alpha 30, Nifty200 Quality 30, Nifty100 Low Volatility 30, Nifty Alpha Index, Nifty Low Volatility 50, Dividend Opportunities 50, Nifty100 Quality 30, Nifty500 Growth 50, Nifty50 Equal Weight, Nifty50 Value 20.

**Factor families:** Value, Quality, Momentum, Low Volatility, Alpha, Dividend and Growth. Nifty50 Equal Weight is presented separately as a **Strategy** rather than an independent stock-selection factor.

## How to refresh

Use **GitHub → Actions → India NSE Constituents Refresh → Run workflow**. The page only reads `data/india_holdings/companies.csv`, `constituents.csv`, and `index_status.csv` after the job commits them. This avoids slow NSE access during every Streamlit session.

If some URLs reject cloud downloads, place corresponding authentic CSVs at `data/india_holdings/manual/<slug>.csv` (or the original NSE CSV filename). `--offline` lets you build using local CSVs only. Slugs and official URLs are listed in `india_constituents.py`.

**Data caveat:** A direct download was not possible in the build environment, so the delivered package initially has no actual NSE constituents. It is ready to populate when the GitHub Action or manual CSV imports run; the interface displays accurate coverage status in the meantime.
