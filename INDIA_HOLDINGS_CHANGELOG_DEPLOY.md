# India Sector & Factor Holdings — Historical tracking upgrade

## This release

- Preserves **all existing market intelligence pages**, Company Financial
  Research, Company Financial KPIs, and the separate India Holdings explorer.
- Adds **🔄 Holdings Changes** to India Sector & Factor Holdings (no ranks).
- Tracks valid constituent additions/removals separately for each of 31 NSE
  sector/thematic/factor/strategy indices.
- Preserves distinct source snapshots and retrieval provenance, including
  before/after comparisons and downloadable history reports.
- Adds weight-change and ticker-change events only when the data supports them.
- Uses existing weekday GitHub Actions scheduled refresh. NSE refreshes run
  outside Streamlit, so opening the dashboard does not trigger NSE requests.

## Upgrade steps

1. Extract `nightly_build/` and overlay **its contents** at your GitHub repo root.
   **Keep your existing `data/india_holdings/` data:** raw snapshots, manual
   imports, company exports, current index status, and prior history. This ZIP
   does not include blank generated CSV/JSON files that could replace them.
2. Commit and push, including `.github/workflows/india-constituents-refresh.yml`.
3. Run **Actions → India NSE Constituents Refresh → Run workflow**.
4. Check `data/india_holdings/build_summary.json`. The job should report
   `loaded_indices > 0`, `history_revisions > 0` and change counts.
5. Open **Factor Analysis → India Sector & Factor Holdings → Holdings Changes**.
6. Repeat the workflow after a subsequent update. The first collection is a
   baseline, so **no additions/removals will appear until a second distinct,
   validated snapshot is collected**.

## If no data loads

- Read `data/india_holdings/index_status.csv` for source-specific errors.
- If NSE rejects cloud requests, use the provided source URLs to obtain
  genuine constituent CSV files and save them in
  `data/india_holdings/manual/<index_slug>.csv`.
- Scheduled runs prefer direct NSE downloads and use manual CSVs as a fallback.
  For a deliberate manual import, run:
  `python scripts/refresh_india_constituents.py --offline --from-dir data/india_holdings/manual`.
- If the source changes dramatically, the collector blocks a suspicious size
  drop/turnover so it cannot turn a bad download into a mass removal. Compare
  with NSE, then rerun with `--allow-large-changes` **only after validation**.

## Audit limitations

History begins with the first saved valid snapshot. Earlier index changes
cannot be reconstructed from present-day constituent lists. Events are dated
when a file was fetched, not necessarily when NSE officially added or removed
a security. A successful collection with unchanged constituents creates no
new revision. No implied constituent weights, missing-membership penalties,
financial strength scores or recommendations are calculated.
