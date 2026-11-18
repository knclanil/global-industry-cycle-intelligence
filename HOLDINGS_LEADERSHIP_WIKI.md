# USA Company Holdings Leadership — Methodology

## Sources and verification

18 BlackRock iShares portfolio document endpoints: **7 factor ETFs** (239695, 239728, 256101, 239563, 239725, 239710, 251614) and **11 sector ETFs** (239505, 239511, 239506, 239524, 239508, 239507, 239520, 239503, 239523, 239514, 239522). These are **portfolio IDs**, not verified fund tickers. The provided initial reference date is November 17, 2026. Actual holdings, portfolio identifiers and as-of dates must be verified from the downloaded files; links alone do not establish issuer membership.

## Leadership score

Each verified issuer has a single rank. The score measures **portfolio prominence**, not price momentum, manager buying, or future returns.

- **Factor breadth (45%)** = distinct factor ETFs holding the issuer / 7.
- **Factor conviction (40%)** = average of `min(1, issuer ETF weight / ETF 90th-percentile issuer weight)` across factor ETFs that hold the issuer; zero for factor-unheld issuers.
- **Sector prominence (15%)** = highest normalized within-ETF sector weight rank `(N-r)/(N-1)` across sector ETFs holding the issuer; zero if absent. A sector leader ranks in the top `ceil(10% × N)` holdings by weight. Ties in sector weight receive the same competition rank.

`Base Score = 100 × (0.45 × breadth + 0.40 × conviction + 0.15 × prominence)`.

## Changes and penalties

Compare consecutive **verified, complete** holdings snapshots for the same ETF. A missing or malformed download is **not** a removal. New factor position: +8; factor removal: −10; new sector position: +4; sector removal: −6. Material increases and decreases are scored continuously per **percentage-point** change: factor +4/−5 maximum per ETF; sector +3/−4 maximum per ETF. An ordinary weight change requires both at least 0.10 percentage points and 5% relative change. Adds/removals do not receive a second weight-change adjustment. Net changes are clipped to [−30,+30]. `Final Score = clip(Base Score + Change Score, 0, 100)`. Changes are calculated against the previous valid snapshot, not accumulated indefinitely. The baseline snapshot has no change score. Weight changes can result from market price movements and do not prove trading or net investor flows.

Rank by final score descending; ties break on factor count, factor conviction, then stable issuer ID. The full ranked list is available on **USA Company Holdings Leadership**, with a Top N selector. Galaxy company-node size uses the final score once verified rankings exist; unverified companies are not synthesized.

## Automatic refresh and audit

GitHub Actions runs after US market close on weekdays and supports manual dispatch. It fetches all 18 sources, validates issuer identifiers, equity weights and **actual source as-of dates**, compares the last complete snapshot, and writes Parquet snapshots, ranking, latest changes and an event log to `data/holdings/`. **Fail-closed:** if any source is unavailable or its as-of date cannot be verified, the run reports failure and does not overwrite the previous complete ranking. BlackRock file formats and access restrictions may require a source-specific adapter before the first successful run; scheduled execution does not guarantee upstream availability. Verify the action logs after deployment.

## Limitations

Sector and factor memberships are the composition of the specified ETFs, not a universal classification of all investment factors. ISIN is preferred for issuer identity, with ticker fallback; share classes and identifier changes require additional issuer-master mapping before guaranteed legal-issuer deduplication. Portfolio weight is not investment performance or direct capital flow.

## Additional sources awaiting classification (November 18, 2026)

Ten further BlackRock iShares portfolio IDs have been received: **239740, 239744, 239753, 239739, 239742, 239741, 239751, 239745, 239748, 239750**. They are tracked in `data/holdings/pending_sources.json` but **excluded from the factor/sector score and refresh universe** until their ETF category is verified. This avoids incorrectly changing the factor breadth denominator or assigning sector leadership. Total registered endpoints: **28** (18 classified, 10 pending).

## Refresh failure diagnosis and parser update

The first GitHub Actions run rejected all 18 sources because the previous parser could not verify holdings-as-of dates. The updated parser checks common iShares CSV metadata preambles (including quoted dates with month names), CSV table offsets, and Excel workbook metadata; it never treats the requested URL date as the published holdings date. Live BlackRock responses were not accessible in the build environment, so this adapter is **not yet validated against the actual endpoint response**. If the API returns JSON or a different schema, capture a sanitized response content-type and the first metadata lines for a source-specific adapter. No source failure should be interpreted as a removed holding.
