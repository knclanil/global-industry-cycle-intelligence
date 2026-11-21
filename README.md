# Repair: USA and India research pages missing from sidebar

## Root cause established

The published GitHub `main/app.py` (inspected November 21, 2026) still contains the old USA and India sidebar definitions; it has no `USA Investment Opportunity Screener` / `USA Company Deep Dive` or equivalent India routes. The earlier ZIP **did not automatically modify your repo**. In particular, the earlier install scripts only change `app.py` if run in the local repository and the resulting `app.py` is committed/pushed. The earlier India installer also requires a specific sidebar layout and can fail if older pages remain.

## INSTALL — Windows / GitHub Desktop

1. Open **GitHub Desktop → Repository → Show in Explorer**. This is your real local repo (has `app.py`, `.github`, etc.).
2. Extract this ZIP and **copy everything inside it** into that repository folder, preserving the `scripts/` folder. **Do not replace `app.py` manually.**
3. In the repository folder double-click **`INSTALL_WINDOWS.bat`**. You should see `SUCCESS: updated app.py` (or `ALREADY INSTALLED`). The installer edits only the local `app.py` sidebar lists, page icons and dispatch routes, and validates syntax and that required UI modules exist.
4. In GitHub Desktop verify the **Changes** tab includes `app.py` and the six `*_research_*` / `*_opportunity_ui.py` / `*_deep_dive_ui.py` files.
5. **Commit to main**, then **Push origin**. **Commit alone is not enough** for the deployed app.
6. Open GitHub.com `main/app.py`, confirm it contains `USA Investment Opportunity Screener`, then refresh/reboot the Streamlit app. Confirm the sidebar has both regions' new pages.

Expected navigation:

- India: Asset Flow → Sector → Factors → Investment Opportunity Screener → Company Deep Dive (old overlapping India analysis pages removed from India navigation only; their modules remain).
- USA: Asset Flow → Sector → Factors → Investment Opportunity Screener → Company Deep Dive (preserves other existing USA pages).
- All Knowledge Graphs stay unchanged.

For terminal usage: `python scripts/install_research_navigation.py` then `python scripts/install_research_navigation.py --check`.

If you still see no changes after push, check: (a) GitHub Desktop correct repository/branch, (b) `app.py` appears in the **committed** files, (c) `main/app.py` online includes both page labels, (d) Streamlit app is configured for this repo/branch and entrypoint `app.py`, (e) Streamlit deployment logs show no import error.

## Data and research readiness

Pages appear with the navigation fix, even if financial CSVs have not been generated. They will show missing financial fields honestly. To generate snapshots from previously cached data, run `python scripts/build_usa_research.py` and `python scripts/build_india_opportunity_dataset.py` in the repo as appropriate. Real company valuations and comparison scores require populated financial data and suitable quote coverage.

## Safety

No edits to knowledge graphs, price and factor calculations, workflows or saved market data. Installer is idempotent and fails without writing if baseline cannot be parsed/validated. The ZIP bundles the previously prepared pages and data loaders. No live deployment has been executed by this assistant.
