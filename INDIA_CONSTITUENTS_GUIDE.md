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

## Historical constituent tracking (new)

Every successful NSE refresh compares that index's latest validated list with
its previous validated list. **The first validated list is a baseline, not a
mass addition.** Only subsequent observed changes generate events. The
existing weekday GitHub Actions job automatically runs this comparison and
commits the files; Streamlit never downloads source data during page loads.

New **🔄 Holdings Changes** tab includes:

- An audit trail of index-specific **Added**, **Removed**, **Symbol Changed**,
  and **Weight Changed** events (when weights are published on both dates).
- Searchable, filterable changes with the source index, NSE symbol, ISIN,
  old/new published weights if available, and time the change was **observed**.
- Per-index immutable snapshot history and a constituent-count trend.
- A two-snapshot comparison and CSV exports for events and differences.

### Storage

- `data/india_holdings/history/<index_slug>/<revision_id>.csv` — preserved
  validated constituents for each **distinct** observed state. Unchanged source
  files, including changes in row order, do not create another version.
- `data/india_holdings/history/<index_slug>/revisions.csv` — per-index revision
  provenance and observed differences, with first-collection baseline.
- `data/india_holdings/history/<index_slug>/events.csv` — index-specific events.
- `data/india_holdings/index_revisions.csv` and `holding_changes.csv` — combined
  read-only dashboard exports built from the per-index historical records.
- `data/india_holdings/index_status.csv` — refresh status and per-run deltas;
  `build_summary.json` — current coverage plus per-run and historical totals.

On upgrading from an earlier version that already has `snapshots/<slug>.csv`,
the previous successful file is saved as a **legacy baseline** before a fresh
validated download is compared against it. Previously unsaved dates cannot be
recreated retroactively.

### Safety and interpretation

- Download errors or invalid HTML/CSV never count as company removals. Existing
  verified snapshots are retained. A reduction below 70% of the prior index
  size or turnover above 60% is blocked for human review; if it is a genuine
  large index change, rerun with `--allow-large-changes` **only after checking
  the source**. The error is reported in the Data Coverage tab.
- An addition/removal is **from that particular index**; it does not imply a
  company entered/left India's stock market or the consolidated universe.
- If a symbol changes but the ISIN remains the same, it is logged as a
  `Symbol Changed` event, not a removal and addition. When one date lacks an
  ISIN, a unique symbol can serve as a safe fallback.
- A weight change is only measurable when both snapshots explicitly publish
  weights. Newly available/absent weight values are not reported as changes.
  A change needs to be at least **0.01 percentage point** to avoid rounding noise.
- Observations are stamped with the UTC **retrieval** time, **not** the official
  effective date, rebalance date, or corporate action announcement date.
- These logs contain **no rankings, negative points, synthetic weights, or
  fabricated historical events**.

To run a local collection and append history:

```bash
python scripts/refresh_india_constituents.py --from-dir data/india_holdings/manual
```

The daily job tries NSE first; if NSE fails, an authentic local file is used as
fallback. A fallback that contradicts a prior direct-NSE snapshot is blocked
until reviewed to prevent reintroducing old holdings. To deliberately import a
new manual CSV when NSE is accessible, use `--prefer-manual`.

For a fully offline import of authentic manually downloaded NSE constituent CSVs:

```bash
python scripts/refresh_india_constituents.py --offline --from-dir data/india_holdings/manual
```

The scheduled workflow now uses `--require-data`: if **none** of the 31 index
sources can be loaded, the workflow is marked failed rather than silently
reporting success. Diagnostics are still committed by the final `if: always()`
step to help identify which downloads were blocked.

**Historical tracking starts with the first valid collection.** If all 31
sources remain uncollected, the page cannot show historical holdings events.
