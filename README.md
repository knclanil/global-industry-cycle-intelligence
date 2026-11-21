# USA research page visibility fix — verified against the public `main/app.py` on 2026-11-21

The public `app.py` already registers **India** Investment Opportunity Screener and Company Deep Dive. The three USA modules (`usa_opportunity_ui.py`, `usa_company_deep_dive_ui.py`, `usa_research_data.py`) are present, but the USA navigation currently lists only Asset Flow, Sector, Factors, and USA Analysis. The USA pages also lack page icons and render branches.

## Installation

1. Extract this ZIP. Copy **`scripts/enable_usa_research_navigation.py`** into the matching `scripts` folder in your repository, and copy `INSTALL_WINDOWS.bat` into the repository root.
2. In the repository root, double-click `INSTALL_WINDOWS.bat` (or run `python scripts/enable_usa_research_navigation.py`).
3. Confirm `SUCCESS: app.py updated`. In GitHub Desktop, verify **`app.py` is changed**, then commit and **Push origin**.
4. Refresh Streamlit. Open the USA sidebar group. The items will be **USA Asset Flow → USA Sector → USA Factors → USA Investment Opportunity Screener → USA Company Deep Dive**.

Only `app.py` is modified by the script. The old USA Analysis navigation entry is hidden, but the analysis code remains in the repository. India, Global, all Knowledge Graphs, and financial workflows are unchanged.

If your local `app.py` has changed materially since the public version inspected, the installer fails without overwriting it. Existing USA page modules must be present; the installer checks this before making changes.

The update has been checked statically; live Streamlit deployment is not verified.
