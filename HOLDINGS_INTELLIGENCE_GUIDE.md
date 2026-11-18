# Holdings intelligence — operations and methodology

## Find the page
Open the Streamlit app, expand **GLOBAL INTELLIGENCE**, then select **USA Company Holdings Leadership**. The page reads `data/holdings/company_rankings.parquet` and `latest_holdings.parquet`. Both must be committed to the deployed branch. The Galaxy is under **Global Capital Intelligence Network**.

## Collection
The scheduled GitHub workflow `.github/workflows/holdings-refresh.yml` downloads issuer-dated holdings, validates the active sources and stores Parquet snapshots. The 10 pending sources are parsed but excluded until classification is verified. Missing data never implies a removed holding.

## Interpretation
The base ranking combines 45% factor breadth, 40% ETF-relative portfolio weight (called factor conviction for convenience), and 15% sector prominence. ETF weights reflect index construction and price changes, not necessarily active decisions. Holdings-weight changes do not establish flows or trades. Change events compare consecutive verified snapshots and must never be inferred from failed downloads.

## Readiness checks
1. Confirm GitHub Actions log prints `Saved ... company rankings`.
2. Confirm `data/holdings/company_rankings.parquet` and `latest_holdings.parquet` exist in the branch deployed by Streamlit.
3. Restart Streamlit if the page uses a stale deployment.
4. Open the ranking page, search a ticker, and expand its holdings.
5. In the Galaxy, select a company node to inspect its verified connections.

## Caveats / remaining work
Company issuer identity can be ambiguous without a stable issuer identifier; ticker-based matching must be treated cautiously. Some registered 'factor' ETFs are broad index funds; validate source categorization before interpreting factor breadth as independent factor diversification. The historical change engine requires multiple distinct issuer-dated snapshots to produce informative change signals.
