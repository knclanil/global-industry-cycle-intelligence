# USA Fundamental Rankings — Direct Visibility Fix

## Why you did not see rankings
The earlier package only installed the ranking section if `INSTALL_WINDOWS.bat` successfully altered `company_kpi_metrics.py`. The public `main/app.py` still routed the USA Financial KPIs page straight to `render_company_kpi_metrics()`, and `company_kpi_metrics.py` contained no ranking call. The public ranking CSV was also absent. Thus simply adding the ranking UI file or a successful collection run did not make a ranking section appear.

## This full-code fix
- Replaces **app.py** with a complete version that calls `render_usa_fundamental_rankings()` immediately before the existing USA Financial KPIs renderer. Existing USA/India/Global navigation and the existing KPI module remain unchanged. **No installer needed**.
- Includes the full ranking UI and the existing automated SEC+quote refresh/rank generation scripts and workflow from the previous bundle.
- Defaults to **All verified companies**, so the table will not appear completely blank when zero companies qualify.
- Does **not** fabricate missing ranks. If `data/usa_research/fundamental_rankings.csv` is missing, the section clearly says so.

## Install
1. Extract this ZIP; copy its contents into the root of your GitHub Desktop repository (merge `.github/` and `scripts/`).
2. Review the change in `app.py`: specifically the `USA Company Financial KPI Intelligence` route.
3. Commit and **Push origin**. Streamlit should show a `Fundamental Rankings` header under **USA → USA Financial KPIs** even when the ranking dataset is missing.
4. GitHub → Actions → **USA Company Fundamentals, Quotes and Ranking Refresh** → Run workflow to publish `data/usa_research/fundamental_rankings.csv`. The workflow is scheduled for weekdays too. Check both GitHub Actions success AND the CSV on main.
5. Hard refresh the deployed Streamlit page. Confirm Streamlit deploys the `main` branch and `app.py`.

## Notes
The workflow depends on an existing `SEC_USER_AGENT` secret and `contents: write` permission. Cached data collection can be incomplete, so 0 ranked companies is possible when any of five fields is absent. The financial sources StockAnalysis and Finviz are reference links; SEC handles statements and existing Yahoo quotes handle market cap. No live run was performed here.
