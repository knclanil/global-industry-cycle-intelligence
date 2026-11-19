# India Sector × Factor Overlap & Membership Leadership

## What the new page does

The **India Overlap & Leadership** page ranks observed NSE company index
memberships in three separate views: Combined (requires both factor and sector
or thematic coverage), Factor-only, and Sector/Thematic-only. It also provides:

- Exact cross-index factor membership patterns, such as Nifty50 Value 20 vs
  Nifty200 Value 30 vs Nifty500 Value 50, with unique-company counts.
- Pairwise within-family intersections, Jaccard percentage, source index names,
  and symbol lists.
- A Sector × Factor heatmap with drill-down to actual NSE symbols and ISINs.
- Per-company audited memberships and direct access to India Financial KPIs,
  Yahoo Finance and Screener's *external* consolidated research page.
- Optional Yahoo financial KPIs alongside the ranking, never included in score.

The underlying NSE collection keeps the 31 user-supplied official indices, all
raw CSV snapshots, holdings history, and source traceability. The precomputed
page needs no network requests and does not wait for Yahoo financial results.

## Membership indicator formula — v1

This is **not** fundamental quality, current stock valuation, past performance,
capital weightage, or an investment recommendation. Its purpose is to surface
cross-index constituency agreement without inventing unavailable weights.

### Factor (F) — 0 to 100

- Family count = number of distinct factor families (Value, Momentum, Quality,
  Low Volatility, Alpha, Growth, Dividend) in which the company appears.
- Extra confirmations = count of additional indices after the first observed
  index in each factor family. Value 20 + Value 30 + Value 50 gives two extras.

`F = 70 × min(family_count / 4, 1) + 30 × min(extra_confirmations / 3, 1)`

This rewards distinct factor exposure more heavily than variants of the same
factor. The Nifty50 Equal Weight *Strategy* is shown but not a separate factor.

### Sector/Thematic (S) — 0 to 100

A company with at least one NSE sector or thematic membership receives 65
points. It gains up to 25 more points for up to two **additional distinct
sector/theme buckets**, plus 10 points for appearing in both a sector and a
thematic index.

`S = 65 + 25 × min((bucket_count − 1) / 2, 1) + (10 if sector + thematic, else 0)`

Bank/PSU Bank/Financial Services memberships count as **one** sector bucket.
Oil & Gas/Energy count as **one**. The source indices are still displayed
separately. When no sector or theme membership exists, S is **N/A**, not zero.

### Combined (C) — 0 to 100

`C = 0.5 × F + 0.5 × S − 0.20 × |F − S|`

Only companies with both F and S appear in the Combined ranking. Sector-only
companies can appear in Sector ranking, factor-only in Factor ranking. Equal
scores receive equal competition ranks; sorted ties use breadth and symbol as
display tie-breakers. No fake zeros are introduced.

### Eligibility / absence caveat

Nifty 50, 100, 200 and 500 are overlapping parent universes, not Large, Mid and
Small Cap portfolios. We **do not apply negative points for missing index
selection** because parent-index eligibility and all strategy selection
conditions are not validated by this source set. Factor Membership Patterns
show absences transparently without turning them into unsupported penalties.

### Weightage and financial context

NSE constituent CSVs downloaded so far contain no published weights. This
model assumes **no index weights**; weight 0 and missing weight are not
interchangeable. A future enhancement can use official complete weights or
published top-10 weights with clear coverage labels. Cached Yahoo financial
snapshots may be shown beside membership ranks, but they are not a constituent
weight and do not affect the ranking. Screener.in links are outbound only.

## Data files

| File | Description |
|---|---|
| `data/india_holdings/constituents.csv` | Verified source memberships, each NSE index and company key |
| `data/india_holdings/leadership_companies.csv` | Per-company scores, separate ranks and source evidence |
| `data/india_holdings/factor_index_overlaps.csv` | Pairwise overlaps within each factor family |
| `data/india_holdings/factor_membership_patterns.csv` | Exact membership-pattern counts and companies |
| `data/india_holdings/sector_factor_overlaps.csv` | Unique sector-index × factor-family intersections |
| `data/india_holdings/leadership_build_summary.json` | Build timestamp and data quality totals |

## Run and deploy

1. Merge the updated project contents into the root of your repo (the ZIP has a
   `nightly_build/` directory; copy its **contents**).
2. **Preserve** your tracked `data/india_holdings` snapshots and change history.
3. Run **Actions → India NSE Constituents Refresh**. It will collect NSE data,
   recompute overlap exports, and commit them to the repository.
4. If the 31 current constituent files are already committed, run
   `python scripts/build_india_overlap_rankings.py` locally and commit only the
   generated ranking files; this is entirely offline.
5. Open **Factor Analysis → India Overlap & Leadership**.

No part of this feature downloads constituents or financials in Streamlit.
The first rankings require valid saved NSE constituent records.
