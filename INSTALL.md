# USA filing-level XBRL recovery — repository overlay

Copy the **contents** of this ZIP into the root of `global-industry-cycle-intelligence` (merge `scripts/`, `tests/`, `.github/`). Commit and push once. Existing dashboard and rankings layout are unchanged.

Run GitHub Actions > **USA Company Fundamentals, Quotes and Ranking Refresh**. Recommended first run: `sec_limit=0`, `quotes_limit=250`, `filing_limit=125`. Scheduled weekday runs automatically continue through the remaining eligible CIKs because successful and failed attempts are cached and published to the repository. Use `filing_limit=0` only if comfortable with a long run and SEC access limitations.

New artifacts: `data/usa_research/filing_xbrl_cache/<CIK>.json` (per-filing extracted observations) and `data/usa_research/filing_xbrl_recovery_report.json`. Existing `fundamental_rankings.csv` and `fundamental_ranking_report.json` are rebuilt after extraction.

SEC access requires the already configured `SEC_USER_AGENT` secret with a real contact email. SEC can block access to filing archives from GitHub-hosted runners; failures are recorded and retried after 14 days. This pipeline does not bypass restrictions.

**Safety and limitations:** The extractor accepts consolidated annual facts from whitelisted US GAAP concepts, and never guesses company-specific taxonomy meanings. Optional reviewed custom mappings can be stored in `data/usa_research/xbrl_aliases.json` as `{ "companyprefix:CustomTag": "OperatingIncomeLoss" }`, but must be manually verified for semantics and unit. It processes the latest 10-K or 10-K/A listed in recent SEC submissions, not all historical annual filings. It cannot guarantee 100% KPI coverage. Existing SEC CompanyFacts are preserved. No StockAnalysis/Finviz scraping.

Test locally: `python -m pip install beautifulsoup4 pandas` then `python -m unittest discover -s tests -p 'test_usa_filing_xbrl_recovery.py' -v`.
