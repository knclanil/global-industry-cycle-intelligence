# Refined research terminal — design release

This package is a direct continuation of `global-industry-financial-and-overlap-reliability-fix.zip`.

## Visual system

- One global Inter/Segoe UI fallback font stack, deep navy (#0B1220), unified cyan (#51B7E8), slate borders (#2A3C55).
- Compact KPI tiles, consistent card radius, quieter headings, tab navigation and sidebar active-page treatment.
- Shorter visible navigation labels (internal route identifiers are unchanged).
- An unobtrusive breadcrumb with the current section and page.
- India sector × factor matrix is displayed as a heatmap with exact figures and CSV available in a disclosure.
- A collapsible NSE membership-frequency chart highlights index membership breadth without changing any ranking.
- Sector/factor financial coverage remains a chart with exact financial coverage table and export.
- Percentage, multiple and count formatting improved where the data semantics are known.
- Redundant descriptive paragraphs moved to optional disclosure sections or abbreviated.

## Data integrity

The update changes presentation only. It does not invent missing SEC/NSE/Yahoo/Screener values, infer index weights, replace financial formulas, or fetch external data during navigation. It preserves source/diagnostic tabs.

## Deployment

Unzip and copy the **contents** of `nightly_build` into the repository root. Preserve any previously downloaded `data/india_holdings`, `data/india_financials`, and SEC cache directories; this package contains only the baseline placeholders that were included in the source project. Commit/push then restart Streamlit.

## Testing

- Python compilation and 59 India-specific tests pass in the available build environment.
- Full test suite has an existing Streamlit import/stub problem in the available environment, so an all-green full-suite result is **not** claimed.
- Live browser rendering, source-provider collection, and deployed UI performance have not been verified.
