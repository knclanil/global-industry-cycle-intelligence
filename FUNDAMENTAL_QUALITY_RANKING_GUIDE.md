# Fundamental Quality & Consistency Rankings

New independent page: **Company Financials → Quality Rankings**. Existing **Leading & Lagging** market signals are unchanged; Ranking V2 is not included.

## Purpose

A company with high margins and returns in only one reporting year should not outrank a company that has repeatedly demonstrated good performance. The page uses the median of up to five annual reported observations and a separate stability adjustment.

## Metrics, directions, and weights

| Metric | Weight | Preferred direction |
|---|---:|---|
| Return on equity (ROE) | 18% | Higher; require positive book equity |
| Debt / equity | 13% | Lower; require positive book equity |
| Current ratio | 10% | Higher |
| Operating margin | 15% | Higher |
| Net profit margin | 13% | Higher |
| Revenue growth | 12% | Higher; based on annual changes |
| Total liabilities / assets | 11% | Lower |
| Dividend consistency | 5% | Higher; explicit reported dividends only |
| Dividend growth | 3% | Higher; at least two valid annual comparisons |

Total 100%. Annual medians reduce sensitivity to unusual years. Per metric, peer percentiles are calculated within the same region and sector only if at least five peers have usable observations. Scores combine 85% of a weighted average of *observed* peer percentiles and 15% stability (ROE, operating, net-margin dispersion). Requires three annual income observations, at least five scored metrics, 60% weighted peer coverage, and two stable profitability signals. If requirements are unmet, show **Unranked / Insufficient coverage** rather than invent a score.

Peer sector classifications come from available holdings/financial source metadata, so mixed subindustries may require more targeted comparisons. Standard leverage and liquidity measures are not valid substitutes for bank and insurer capital/solvency measures; treat those sectors' rankings cautiously.

## Data and markets

- USA: cached, verified SEC XBRL annual Company Facts matched to USA ETF issuer identities.
- Global: presently SEC-reporting issuers held in Global ETFs **only**. Non-US issuers need an additional licensed annual-financial-statement provider. Global and USA ranks remain independent.
- India: saved annual financial statements in `data/india_financials/companies/*.json` from your Yahoo refresh workflow. The dashboard doesn't contact NSE/Screener/Yahoo or perform bulk scraping on page open.
- Historical dividends in SEC filings are *cash paid*, not declared dividends; missing explicit line items are unknown, not zero.
- No current stock valuation, book value per share, market returns, or ETF weights are included in the quality score.

The app reads current snapshots without downloading all companies. Company score results may be empty if providers have incomplete historical statements, especially current assets, current liabilities, and annual dividends. Make additional coverage visible rather than infer missing figures.

## Validation

Run `python -m pytest tests/test_fundamental_rankings_engine.py -q` from the project root.
