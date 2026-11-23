# USA comprehensive SEC recovery update

Copy the `scripts`, `tests`, and `.github` directories into the repository root, preserving the directory hierarchy. Commit and push in GitHub Desktop, then run **USA Company Fundamentals, Quotes and Ranking Refresh**.

This patch adds conservative SEC-only derivations of operating income (gross profit less operating expenses) and current liabilities (total liabilities less noncurrent liabilities), with matching period-end requirements. It also adds selected GAAP concepts, audit evidence, regression tests, and ranking-report workflow summary.

**Do not expect every company to become rankable:** company-specific extension facts are not in SEC CompanyFacts, some periods are absent, and financial institutions remain ineligible under the existing ranking rules. No external website scraping or fabricated KPI values.

Verify `data/usa_research/fundamental_ranking_report.json` and `fundamental_field_evidence.csv` after the run. Baseline: 1,456 ranked, 1,336 incomplete, 139 ineligible.
