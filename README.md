# USA Research Pages — Complete Replacement Source Files

This is a **copy-and-replace** package. No installer or terminal command is required.

## Contents
- `app.py` — complete Streamlit entrypoint with USA and India research pages registered.
- `usa_opportunity_ui.py` — complete USA Investment Opportunity Screener page.
- `usa_company_deep_dive_ui.py` — complete USA Company Deep Dive page.
- `usa_research_data.py` — complete shared USA research data loader and filters.

## Apply
1. In GitHub Desktop choose **Repository → Show in Explorer**.
2. Copy these four `.py` files into the **repository root** (same folder as the existing `app.py`), replacing files with identical names.
3. In GitHub Desktop confirm that `app.py` appears under **Changes**. If it does not, compare with the file in GitHub main; the replacement may already be there or was copied into the wrong folder.
4. Commit and **Push origin**. Verify the committed `app.py` in GitHub `main` includes `USA Investment Opportunity Screener` in `NAV_GROUPS` and `elif page == 'USA Investment Opportunity Screener'` in page routing.
5. On Streamlit Cloud check the app's deployed branch and app entrypoint (`app.py`); allow a fresh rerun or restart if needed.

## Scope
- USA sidebar order: Asset Flow → Sector → Factors → Investment Opportunity Screener → Company Deep Dive.
- India sidebar order remains intact.
- USA old Sector · Factor · Holdings route remains in the file as legacy code, but is removed from USA navigation.
- Global sidebar, Knowledge Graph, and financial-data workflows are not modified.
- USA research pages read existing stored company research data; if that dataset is missing, data coverage may be incomplete. This ZIP does NOT claim to complete live SEC or quote ingestion.

## Validation
- All four included Python files passed offline AST syntax validation.
- The result has not been deployed into your own Streamlit Cloud account or live-tested against the repository's current runtime.

## Source basis
- Current GitHub `main/app.py` opened 2026-11-21. The included full `app.py` is based on the India research pages package's full copy, which has the same navigation/routing layout, with the USA pages added.
