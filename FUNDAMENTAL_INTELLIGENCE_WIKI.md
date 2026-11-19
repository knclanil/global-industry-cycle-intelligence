# Fundamental Intelligence — implementation and limitations

## Scope

The Fundamental Intelligence page reads unique issuers from the verified USA and Global iShares holdings snapshot, retaining independent regional views. It does not change the existing holdings leadership formula, rankings, or orbital graph. Issuers are not identified from ticker alone: SEC CIK mapping requires a ticker match and a company-name similarity check. Ambiguous matches are skipped.

## Data provenance

US issuer financial data comes from SEC EDGAR `companyfacts` XBRL. The source JSON is cached under `data/fundamentals/facts_<CIK>.json`. The SEC directory is cached in `sec_company_directory.json`. Each reported number retains its source taxonomy tag, filing accession, and filing date. Annual observations are selected from 10-K/20-F submissions, including amendments. Latest amended/restated values supersede older observations for the same fiscal period. Derived ratios are calculated locally. A source observation is **not** necessarily the same as the company's latest earnings release. The SEC filing index is loaded separately from SEC submissions and links to the complete original documents.

SEC access requires `SEC_USER_AGENT` (application name and contact email) in the environment or Streamlit secrets, and must comply with SEC fair-access guidance. Refresh is manual and capped at 20 new US issuers per invocation. The dashboard does not yet provide a scheduled SEC refresh.

## Ratios

Operating margin = operating income / revenue. Net margin = net income / revenue. ROE = net income / shareholders' equity. Free cash flow = operating cash flow − capital expenditure. FCF margin = free cash flow / revenue. Cash conversion = operating cash flow / net income. Revenue and earnings growth are annual year-over-year changes. Net debt = current and long-term debt − cash, subject to availability of the SEC XBRL tags. These are research estimates and require review of issuer-specific accounting presentation.

## Provisional score

Four dimensions use sector-relative percentile ranks: Quality (ROE, operating margin, net margin), Growth (revenue and earnings growth), Financial health (net debt; lower preferred), and Cash flow (FCF margin, cash conversion). Each percentile requires at least five observed peers in the same sector. Missing values are excluded, not replaced with zero. At least three dimensions must be populated to display a provisional score, calculated as the unweighted mean of available dimensions. The score is **not** the proposed complete fundamental leadership model: market valuation, capital allocation, earnings quality, specialized bank/insurance/REIT models, and comprehensive global filings are not yet integrated. It must not be used as an investment attractiveness ranking.

## Filings and document access

The company details tab provides historical filing-derived statements, source tags/accessions/dates, and direct links to official 10-K, 10-Q, 8-K, 20-F and 6-K documents when available. Full inline HTML/PDF reading, narrative extraction, AI question answering with section citations, filing-diff analysis, and alerts are **planned, not implemented**. Official filings remain the source of truth.

## Data coverage and caveats

The SEC is primarily a US reporting source; non-US issuers require country-specific regulators or a licensed international data provider. Company name and ticker alone do not guarantee correct issuer mapping. Financial data and market prices have different timestamps. The current version does not fetch prices, market caps, analyst estimates, or valuation ratios. Coverage and source timestamps must be reviewed before interpreting any score. Fiscal periods, accounting policies, sector classifications, XBRL tags, and restatements can limit comparability.

## Next integrations

1. Licensed global filing provider and issuer identifiers (ISIN/LEI/FIGI) with explicit matching.
2. Market prices and valuation with as-of timestamps, plus specialized industry scoring.
3. Automated nightly updates, filing-change alerts and point-in-time historical score snapshots.
4. Auditable filing section extraction, comparison and grounded Q&A.
5. Out-of-sample ranking validation and separate Business Quality / Investment Attractiveness rankings.
