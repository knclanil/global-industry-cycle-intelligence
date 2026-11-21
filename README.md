# Fix missing USA and India Investment Research pages

## Diagnosis (verified against public GitHub main/app.py on 2026-11-21)
The deployed main/app.py lists USA Asset Flow, USA Sector, USA Factors and USA Analysis; it has NO USA Investment Opportunity Screener or USA Company Deep Dive route. India research routes are also absent. The latest *USA financial pipeline* ZIP contains only workflows, scripts, and tests — it does **not** include app.py, the Streamlit research pages, or navigation integration. Its successful deployment cannot create visible pages.

## Do this once in GitHub Desktop (Windows)
1. Extract this ZIP, open the extracted folder and **copy all contents** (including Python files, `scripts`, `.github`, and `INSTALL_WINDOWS.bat`) into your actual local global-industry-cycle-intelligence repository root where app.py lives.
2. Double-click `INSTALL_WINDOWS.bat` **inside the repository root**, not inside the extracted folder. It updates the current app.py safely and confirms four page routes exist. If it fails, do not commit; share the displayed error.
3. In GitHub Desktop, verify Changes includes `app.py` and `usa_opportunity_ui.py`, `usa_company_deep_dive_ui.py`, `usa_research_data.py` (plus three India files). If `app.py` does not appear changed, check if those routes are already present.
4. Commit ALL changes, then **Push origin** to the branch used by Streamlit Cloud (typically main). GitHub.com main/app.py must contain `USA Investment Opportunity Screener` and `USA Company Deep Dive` afterwards.
5. Restart/reload Streamlit app. Its USA nav now shows Asset Flow -> Sector -> Factors -> Investment Opportunity Screener -> Company Deep Dive; India shows the same ordered journey.

## Notes
- This fixes page visibility; it does not guarantee data availability. USA financial figures depend on published `data/usa_research/company_research.csv` from the scheduled USA fundamentals workflow.
- Graph functionality and other market calculations are not edited by the installer.
- Neither deployment nor live data refresh has been run from this environment.
- The included automated USA pipeline is the same prior package, combined here to avoid having to track two different ZIPs.

## Installer sanity check
`python scripts/install_research_navigation.py --check`
