# Source taxonomy grouping — Global Industry Cycle Intelligence

Copy `source_taxonomy.py` to repository root; copy `scripts/build_source_taxonomy.py` to `scripts/` and the test to `tests/`.

Run `python scripts/build_source_taxonomy.py`, then publish the generated CSV with GitHub Desktop. No changes to existing graph code are made by this package.

This groups all **31** registered NSE index/constituent sources into sector/factor families. It explicitly treats Nifty Oil & Gas, Nifty India Defence, and Nifty India Manufacturing as **sector groups** for graph taxonomy, despite the latter two being marked *Thematic* by the NSE source catalogue. All Value-named Factor indexes become family **Value**, etc.

**Important:** Taxonomy mapping is not the same as verified rotation mapping. The CSV intentionally keeps `rotation` blank until you attach a validated price series for each unique source. It also does not change or fabricate memberships; your existing constituent snapshots must exist. The current graph only renders classified signals from `rotation_signals`, so publishing this CSV by itself will not display newly grouped factors/sectors in the graph. A follow-up integration needs to join this taxonomy to membership sources and separately join price-derived rotation by source identity.


## Added US/global ETF classifications
- **iShares Russell 2000 ETF** → **Factor / Small Cap** (requested analytical taxonomy; the ETF tracks small-cap equities).
- **iShares Global Comm Services ETF** → **Sector / Communications** (also supports spelled-out “Communication Services” name).

These exact-name overrides work even when the source category is `ETF`. To use them for global/USA feeds, call `classify_source(source_name, category=source_category)` when building the graph source taxonomy; `build_india_taxonomy()` only exports the registered India indices. **This package does not automatically update your Global/USA graph snapshots or their renderers**; they require the taxonomy join in the data builder and refresh. Original tickers, prices, company memberships, and rotation values remain unchanged.
