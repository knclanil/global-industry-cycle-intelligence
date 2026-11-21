# USA Company Financials — automatic end-to-end refresh

This package replaces the *USA company fundamentals workflow* and its associated collectors with one scheduled pipeline. It uses existing verified iShares US issuer memberships, **SEC EDGAR CompanyFacts for filings**, and existing **Yahoo Finance** as a *price/valuation metadata source* (not Alpha Vantage). India, Global, the Knowledge Graph, and Streamlit navigation are not modified.

## Install once (GitHub Desktop)

Extract ZIP; copy the enclosed `.github`, `scripts`, and `tests` directories into the project root, preserving structure. Commit and **Push origin**. Do not replace `app.py`. The USA Company Fundamentals and Valuations Refresh workflow then runs automatically every weekday at 14:40 UTC. It can also be run manually, without input changes.

**Required existing prerequisite:** the repo's GitHub Actions secret `SEC_USER_AGENT` must be an identifying name and contact email for SEC EDGAR access. If already set from the prior USA pipeline, do not change it.

## Pipeline

1. Use **only verified USA iShares company holdings**, rather than unrelated Global funds.
2. Collect up to 125 new/stale SEC CompanyFacts records per weekday; reuse existing facts. Official SEC ticker-to-CIK registry is cached, and missing/ambiguous CIK matches are never guessed. SEC requests have backoff and failure cooldown.
3. Produce a full company research table **offline from cached SEC facts**. This avoids triggering thousands of SEC requests from the dashboard and avoids `sec_financials.load_company()` performing unbounded web fetches when data is absent.
4. Prioritize fundamental-ready USA issuers for price/valuation collection (up to 125 per weekday). Skip malformed identifiers such as `-` and `2200964D`, and preserve previous valid quotes on provider failures.
5. Rebuild company research with latest quotes. For each issuer, both a current financial statement and a fresh USD quote with P/E or P/B are required for `research_ready=Yes`. Reports explain missing intersection.
6. Publish refreshed SEC caches, quotes, issuer research, and USA coverage reports to `main` from a clean temporary Git worktree with push retries.

### Generated datasets

- `data/usa_research/company_research.csv`: Company Deep Dive and Opportunity Screener inputs.
- `data/usa_research/quotes.csv`: dated source-tagged USD prices and available market multiples.
- `data/usa_research/completion_report.json`: full current coverage, overlap, data gaps.
- `data/usa_research/financial_gaps.csv`: **every company** with missing metrics and readiness reasons.
- `data/usa_research/quote_pilot_report.json`: per-run quote results and malformed symbol exclusions.
- `data/usa_research/collection_report.json`: per-run SEC results and errors.
- `data/research_coverage/fundamental_coverage.json`: combined coverage display, India counts unchanged.

## Integrity / limitations

- `research_ready` means inputs available, **not** an investment recommendation or numeric investment score. Model scores remain missing rather than fabricate peer-comparable valuations.
- Industry-peer ranking and valuations such as EV/EBITDA need additional *verified comparable inputs*. The current pipeline supplies available SEC financials, Yahoo price / market-cap and reported P/E / P/B. Missing metrics stay missing.
- SEC EDGAR returns statements only for eligible US reporting issuers. Some of the 2,931 verified ETF constituents may be foreign issuers, funds, preferred securities, or otherwise outside CompanyFacts coverage. Full 2,931-company fundamental coverage cannot be guaranteed.
- Yahoo Finance is an unofficial data channel; rate limits and terms may restrict bulk availability. A finished automated collection workflow does **not** guarantee that all quotes or ratios will be populated. The automated reports make gaps explicit.
- This is a **local integration package**. The repository's current live branch was not available for full checkout here; the code was compiled and offline regression tested against the previously shared source packages, but the live hosted workflow has not run in this environment.
- The scheduled workflow increments coverage in batches, rather than making thousands of requests at once. Its total time to populate the eligible universe depends on provider responses, GitHub Actions limits and existing caches.
