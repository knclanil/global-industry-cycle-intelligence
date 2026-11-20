# Fundamental Quality & Consistency — Model V3

## What this measures

Business quality ranks **consistent operating performance**, not share-price momentum, ETF membership, or valuation cheapness. USA, Global, and India are separate comparison universes. Companies are ranked only when sufficient verified annual evidence exists. **Single-period India reference ratios are displayed in the separate preliminary snapshot comparison, never promoted to historical rankings.**

## Financial history and eligibility

- The most recent **three to five consecutive annual fiscal periods** are required. Annual records are kept at their original as-of date; an instant balance-sheet item cannot be confused with a full-year income or cash-flow value.
- Financial ratios use the **historical median**, not solely the most recent year. Growth uses consecutive annual revenue and calculated EPS, with additional 3–5 year CAGR metrics. EPS is derived from annual net income and stated shares when available; a provider's displayed EPS is not substituted.
- Each comparable KPI receives an **industry-within-region percentile**. At least **five valid peer observations** are required for a percentile. A company with no appropriate sector peer set remains unranked; the system never pools mismatched industries to manufacture percentile scores.
- To rank, a company needs ≥3 annual years, ≥5 supported percentile KPIs, **≥70% of the applicable dimension weights**, historical consistency, and financial-strength evidence.
- Missing observations remain missing. **Missing dimensions are not reweighted upward** to inflate a partially covered company's score. The score is a conservative 0–100 evidence-based score.
- Accounting ROIC is displayed as unavailable when taxes and invested capital cannot be reliably reconstructed. It is not inferred from ROE.

## Nonfinancial-company business quality

| Domain | Weight | KPIs and evidence |
|---|---:|---|
| Profitability & capital efficiency | 25% | Historical ROE, operating margin, net margin. ROIC is only used if defensible underlying inputs are available; current V3 does not fabricate it. |
| Financial strength | 20% | Debt/equity, liabilities/assets, current ratio. Negative equity invalidates ordinary ROE/debt-equity comparisons. |
| Growth quality | 20% | Multi-year revenue CAGR and calculated EPS CAGR, instead of favoring one exceptional revenue-growth year. |
| Cash flow quality | 20% | FCF margin, cash conversion, positive FCF years, FCF CAGR, and reported dividends / dividend growth where observed. CFO − absolute capex is the FCF proxy. |
| Historical consistency | 15% | Normalized variability in profitability and revenue growth, plus recurring positive earnings and verified cash-generation history. |

**Individual domain scoring:** each observed KPI is percentiled against same-region, same-sector peers. A domain must have at least half its specified KPIs, rounded up, to count. Its score is the average of the available eligible percentiles. The final business-quality score is the **sum of domain score × fixed domain weight** for eligible domains, not a renormalized average over missing domains.

## Financial institutions

Banks and similar financial institutions require a distinct **35% profitability / 25% financial strength / 25% growth / 15% consistency** domain weighting. Traditional industrial current-ratio, cash-flow and debt-to-equity comparisons are excluded in this provisional branch. Insurers, NBFCs, and REITs should be further subdivided as complete sector-specific fields become available. The model does not claim that current provisional financial-sector metrics substitute for asset quality, regulatory capital or underwriting analysis.

## Dividend and cash flow caveats

- Missing dividends do not mean zero dividends. A verified reported zero counts as a zero dividend observation.
- Companies that retain earnings instead of distributing dividends are **not automatically low quality**; dividend metrics provide only limited supporting evidence.
- Provider gross cash-flow amounts, sign conventions and annual durations should be verified before drawing conclusions; financing cash flows are not equivalent to capex.

## India reference snapshot: separate, not a historic rank

The `data/india_financials/reference_snapshot.csv` reference can populate the **India Company Financials** table and its clearly labeled **Snapshot Comparison** for research. It does not contain enough period-specific evidence for the V3 consistency rank, internally reconstructed Graham EPS, or DCF. To activate verified rankings, run the `India Company Financials Refresh` workflow with `limit = 0` and confirm that annual statement JSON files were saved in `data/india_financials/companies/`. That can take multiple runs and is subject to provider availability.

## Valuation must remain separate

**Calculated EPS** = attributable annual common earnings ÷ weighted-average common shares (period-end shares are an explicitly labeled approximation). It is accounting profit per share, not cash flow per share and not a website's published EPS. **Graham Number** = √(22.5 × positive calculated EPS × positive common book value per share). DCF Bear / Base / Bull currently use a *simplified, normalized CFO−capex per-share proxy*; they are not a rigorously reconciled FCFF/WACC or FCFE valuation. Graham, DCF, and current market price do not alter business quality rank. Do not average them into one implied market price.

## Display and diagnostics

Ranking table includes the overall score, domain scores, coverage, number of annual periods, original financial KPIs and company source. Unranked companies can still be viewed separately. Financial reporting dates, peer availability and collection errors should be checked before comparing companies. India snapshot scores are **not comparable** to multi-year quality scores.

## Rebuild and deployment

Refresh the actual US SEC and India provider snapshots first. Deploy code and data together. Do not replace data directories with empty template files. Existing market-based Leading & Lagging rankings are independent and unchanged by Model V3.

**Document version:** 2026-11-20 — Fundamental Quality Model V3.
