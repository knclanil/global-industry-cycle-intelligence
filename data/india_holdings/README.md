# India NSE Sector & Factor Constituent Data

The dashboard page is an **offline, read-only** explorer of 31 NSE constituent CSVs. It never requests NSE data during page rendering. No ranking, eligibility penalty or imputed constituent weighting is used.

## Populate the data

**GitHub Actions:** Select **Actions → India NSE Constituents Refresh → Run workflow**. The job downloads each NSE CSV, validates the expected constituent headers, stores raw snapshots, and commits:

- `snapshots/<index_slug>.csv`: last successfully parsed raw CSV from NSE or a manually supplied file.
- `snapshot_meta/<index_slug>.json`: retrieval time and provenance.
- `constituents.csv`: one row per company/source-index membership.
- `companies.csv`: deduplicated company directory with all memberships preserved.
- `index_status.csv`: source status, counts and failures (failed sources keep previous valid snapshots).
- `build_summary.json`: coverage summary.

**If NSE blocks automated requests (403):** Download the source CSV in your browser and place it in `data/india_holdings/manual/<index_slug>.csv` (or its original NSE CSV filename) in GitHub. The workflow will import that file first and label its origin `manual_import`. The file must be an authentic constituent CSV with `Company Name` and `Symbol` columns. Run the workflow again. If no valid inputs exist, the UI displays collection status instead of manufactured companies.

To import local files without any network access:

```bash
python scripts/refresh_india_constituents.py --offline --from-dir data/india_holdings/manual
```

To fetch only one changed index while keeping all others' existing snapshots:

```bash
python scripts/refresh_india_constituents.py --index nifty500_value_50
```

See `INDIA_CONSTITUENTS_GUIDE.md` in the repository root for page details and the list of index slugs.

## Interpretation & safety

- **Company ID:** ISIN when valid; if an index omits ISIN, reconcile its symbol only when exactly one known ISIN has that symbol. Otherwise use a `SYMBOL:` provisional identifier, marked as such. ISINs identify securities; do not assume all share classes are the same corporate security.
- **Universe:** Nifty 50, Nifty 100, Nifty 200 and Nifty 500 are overlapping parent universes, **not** three exclusive large/mid/small capitalization buckets.
- **Missing index membership:** Merely means not in a downloaded index list; it does not prove the company was eligible or rejected.
- **Weights:** Source percentage only, when the uploaded/downloaded file includes an explicit weight column. Otherwise blank/N/A. No guessed top-10 weights.
- **Date:** A retrieval timestamp describes when the CSV was collected, **not** the official effective/rebalance date.
- **Snapshot completeness:** Each of the 31 index sources has its own status; a failed request cannot delete its previously parsed snapshot.

## Observed change tracking

The same background refresh preserves distinct, validated versions under
`history/<index_slug>/` and materializes `index_revisions.csv` and
`holding_changes.csv` for the dashboard's **Holdings Changes** tab.
Initial collection establishes a baseline, not an addition. Subsequent
successful collections record index-specific additions, removals, ticker
changes, and published constituent weight changes, when verifiable.
Failed/suspicious sources retain prior data, never triggering false removals.
See `INDIA_CONSTITUENTS_GUIDE.md` for details, date semantics, and safeguards.
