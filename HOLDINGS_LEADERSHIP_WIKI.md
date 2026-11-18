# USA & Global Company Holdings Leadership — Current Methodology

**Status:** Documents the implementation supplied in the November 18, 2026 performance-weighted leadership build. This package is documentation prepared for repository publication, **not a live GitHub Wiki edit**.

## Purpose and interpretation

This is a **performance-aligned ETF holdings ranking**, not a direct company stock-return ranking, capital-flow measure, investment recommendation, or proof of ETF manager buying. A company's holdings weight is not its own share-price performance. All input performance scores must be verified and aligned to the same observation period.

## Separate ranking universes

| Universe | Factor ETF count | Sector ETF count | Total configured |
|---|---:|---:|---:|
| USA | 7 | 11 | 18 |
| Global | 5 | 10 | 15 |

USA factor IDs: `239695, 239728, 256101, 239563, 239725, 239710, 251614`.

USA sector IDs: `239505, 239511, 239506, 239524, 239508, 239507, 239520, 239503, 239523, 239514, 239522`.

Global factor IDs: `271538, 275382, 239499, 239605, 271540`.

Global sector IDs: `239740, 239744, 239753, 239739, 239742, 239741, 239751, 239745, 239748, 239750`.

Portfolio IDs are data-source identifiers, not customer-facing ETF tickers. Fund titles are read from verified source files. No cross-universe pooling of ETFs, score normalization, company ranking, or breadth denominators.

## Calculation, exactly as implemented

For a company *i* in an ETF *j*, with reported portfolio weight `w_ij`:

`Conviction_ij = min(1, w_ij / max(P90_j, 1e-8))`

where `P90_j` is the 90th percentile of **reported holding weights within ETF j**. This makes the holding weight relative to that ETF's distribution. The implemented code does not clamp negative weights at zero; source validation should ensure eligible equity weights are appropriate.

For each category (sector or factor), use only ETF positions that have a verified performance score `P_j` between 0 and 100:

`SectorAlignment_i = mean(Conviction_ij × P_j)` over scored sector ETF positions holding *i*.

`FactorAlignment_i = mean(Conviction_ij × P_j)` over scored factor ETF positions holding *i*.

The mean is **across matched ETF positions**. It is not a ratio of the sum of weighted performance to the sum of company weights; it is not a pure average of sector performance either.

`Base_i = (SectorAlignment_i + FactorAlignment_i) / 2` when both are available.

When only one component is scored, `Base_i` equals that available component (no zero penalty for an absent category). When neither is scored, `Base_i = 50` **as a neutral provisional placeholder**, not verified performance.

`ETFCount_i = number of distinct configured ETF portfolio IDs holding company i`.

`BreadthBonus_i = 10 × ln(1 + ETFCount_i) / ln(1 + UniverseETFCount)`.

`LeadershipScore_i = min(100, Base_i + BreadthBonus_i)`.

Thus, the effective 50% sector / 50% factor weighting is **conditional on both being scored**. The bonus is additive and can contribute up to 10 points. Because the base can already reach 100, the additive bonus can saturate the final score at 100; the ranking is not a convex 50/50/10 weighted average.

### Ranking and tie-breaks

Sort by leadership score descending, then distinct ETF count descending, then stable issuer ID ascending. The displayed score is rounded to two decimals. Holdings change events do **not** modify this version's leadership score (`change_score = 0`).

### Performance coverage flags

- **Verified:** all ETF positions holding that company have matched valid performance scores.
- **Partial:** some, but not all, have scores.
- **Missing:** none have scores; neutral base 50 is provisional.

A company with Partial/Missing status should **not** be presented as a confirmed leader. The current implementation checks per-company ETF position coverage; operational source freshness and benchmark methodology require separate validation.

## Illustrative example (not live results)

A company has two sector ETF holdings: convictions 0.80 and 0.50, ETF performance scores 90 and 30. Sector alignment = `(0.80×90 + 0.50×30)/2 = 43.5`.

It also has two factor ETF holdings: convictions 0.90 and 0.60, scores 85 and 40. Factor alignment = `(0.90×85 + 0.60×40)/2 = 50.25`.

Base = `(43.5 + 50.25)/2 = 46.875`. With 4 distinct ETFs in the USA 18-ETF universe, bonus = `10×ln(5)/ln(19) ≈ 5.47`, giving **final ≈ 52.34**.

A large position in a lagging ETF still contributes positively when the performance score is above zero, but less than an equivalent position in a leading ETF. This formula does **not** explicitly subtract a laggard penalty.

## Performance data: required, not automatically wired

Provide `data/holdings/etf_performance_scores.csv` with columns:

```csv
portfolio_id,region,performance_score
```

`region` must be `USA` or `GLOBAL`, each portfolio ID must belong to that universe, and scores must be numeric within 0–100. Duplicated `(region, portfolio_id)` keys are rejected. **No actual performance values are bundled or invented.** The November 18 build loads this CSV if available; **direct automatic connection to the dashboard's sector/factor rotation score calculation is not yet implemented**. Align all scores to a consistent period before ranking.

## Holdings identity, normalization and refresh

Within a single ETF, identical verified issuer/ticker and country positions should be consolidated; tickers reused by different issuers/countries must not be merged. Prefer stable verified issuer identifiers and review ambiguous share classes or symbols. The existing ingestion pipeline should be checked for complete implementation of these safeguards before production use.

The refresh workflow uses downloaded holdings and published as-of dates, not a URL date as proof of freshness. Failed or incomplete source downloads should not be interpreted as sales or overwrite the last complete snapshot. Holdings additions, removals and material weight changes are available as **informational events**, not additional leadership-score bonuses. The scheduled GitHub Actions workflow requires successful live verification of all configured sources.

## Key limitations and testing

The score measures **relative prominence in performance-ranked ETFs**. It does not establish company-specific momentum, investment returns, causal capital flows, or forecast performance. Coverage differences can change ranking comparability. The 90th-percentile normalization can saturate large holdings, and the additive bonus can saturate high scores. Validate source completeness, same-date performance windows, cross-country issuer matching, sensitivity to score/bonus weights, ranking stability and forward returns before treating the model as predictive.

**Previous methodology (superseded for the primary score):** 45% factor breadth + 40% factor conviction + 15% sector prominence, plus holdings-change adjustments. Do not use this older equation to interpret rankings from the current build.
