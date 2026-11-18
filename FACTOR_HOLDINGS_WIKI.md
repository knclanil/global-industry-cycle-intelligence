# Factor Holdings Comparison — methodology and data validation

## Objective
Find companies selected by several factor portfolios, giving credit for both cross-factor participation and meaningful within-factor allocation. **This is holdings consensus, not a company's fundamental factor score, future return forecast, or actual money flow.** Global, USA, and India are available in **one page**.

## Holdings sources
Upload full constituent weights from the **official issuer** (iShares, Vanguard, etc.) for Global/USA ETFs and official **Nifty Indices** constituent/weight reports for Indian factor indices. The application **does not automatically fetch these files**: issuer endpoints, formats and permissions vary, and unverified price or proxy data must not be mistaken for constituent weights. Supply current complete CSV or XLSX reports; CSV template is available in the page. Map each file to its factor or provide a `factor` column. Required: `company`, `weight` (percentage points such as 2.5), and factor mapping. Recommended: `ticker`, `isin`, `as_of`, `source`.

Use ISIN for cross-factor security matching when possible; otherwise ticker, then normalized company name. Without a stable identifier, cross-listings, share classes and name variants can be incorrectly merged or split. Review results before making decisions. ETF constituent holdings and index constituents may not be identical; do not treat an index report as an ETF's exact live holdings. Match as-of dates and currency/share-class identity.

## Calculations
Let F = number of **selected factors with loaded data**. For company i and factor f, let w(i,f) be the reported portfolio weight as a percent, N(f) be the number of reported constituents, and r(i,f) be its descending weight rank (ties get minimum rank).

- **Factor Count C(i)**: number of factors with a positive reported weight for company i.
- **Top-10 Count**: number of factors where its full-universe weight rank is <= 10.
- **Breadth B(i)** = 100 × C(i) / F.
- **Within-factor rank percentile P(i,f)** = 100 × [1 − (r(i,f) − 1)/(N(f) − 1)] when N(f)>1, otherwise 100.
- **Weight Multiple** = w(i,f) / (100/N(f)). A 3% holding in a 100-stock portfolio has a multiple of 3.
- **Within-factor Weight Score W(i,f)** = 100 × min(Weight Multiple, 5)/5.
- **Rank Strength R(i)** = sum of P(i,f) across held factors / F.
- **Weight Strength W(i)** = sum of W(i,f) across held factors / F.
- **Consensus Score** = 0.40 × B(i) + 0.35 × R(i) + 0.25 × W(i) (default; weights adjustable and must total 100%).

**Absent holdings contribute zero** to R and W because both are divided by all loaded selected factors, not just those holding the company. The ranking therefore rewards both breadth and conviction. These are heuristic weights, not statistically validated alpha forecasts.

### Worked example
Assume 5 factors are loaded. Company A is held in 4, has average within-factor percentile 90 and average within-factor weight score 80. Then B=80, R=4×90/5=72, W=4×80/5=64, and Consensus=0.40×80+0.35×72+0.25×64 = **73.2**. A company held in all 5 factors at negligible weights may have a higher count but a lower consensus score.

## Top 10 versus all holdings
All holdings mode includes all companies in uploaded files. Top 10 mode **filters to companies appearing in at least one factor's top 10** but keeps original full-universe ranks, breadth and scores. Use the Top-10 Count column to find repeated top-ten appearances. Minimum factor count filters the output; it does not change score denominators.

## Quality controls and limitations
- The page shows file coverage, total weights, source filenames and as-of dates. Weights totaling <95% generate an incomplete-data warning; >102% is blocked. These thresholds are practical diagnostics, not proof of completeness.
- Duplicate security IDs within a factor are rejected rather than silently aggregated.
- Missing selected factor files are excluded from the denominator **with an explicit warning**. This means scores across snapshots with different coverage are not directly comparable.
- Do not upload only top-ten files for an all-holdings score: rank percentiles and weight multiples depend on the complete constituent universe.
- Some provider files include cash, derivatives, collateral or non-equity positions. Review and filter those upstream when seeking a pure company ranking.
- ETFs differ in selection rules, number of constituents, concentration, and factor purity; shared large-cap stocks can appear across multiple funds without indicating independent factor confirmation.
- Source files are processed in the user's Streamlit session; this page does not write holdings to a database or repository.
