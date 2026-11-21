# Sector · Factor · Holdings — redesigned workspace

## Purpose
This is a holdings research page, not another market-rotation Knowledge Graph. It answers which companies are members of each verified sector ETF/index and factor ETF/index; where sector and factor exposures overlap; which memberships are shared; and whether underlying financial data exists.

## Installation (GitHub Desktop)
1. Extract this ZIP.
2. Open GitHub Desktop → Repository → Show in Explorer/Finder.
3. Replace the root-level `regional_workspace.py` with the included replacement. **Keep a backup** of your existing file before replacing because your branch may contain later additions.
4. Commit and Push origin. Streamlit redeploys the code. No cache rebuild is required if the existing dashboard CSVs contain data.

## Views
- **Overview:** unique-company exposure counts across sector sources and factor families.
- **Company explorer:** multiselect filters, search, and CSV export.
- **Sector × Factor overlap:** live counts derived from company membership lists (works even when the old `*_sector_factor_matrix.csv` is empty).
- **Index / ETF directory:** saved index names and constituent totals.
- **Financial coverage:** actual observed company-level metrics; missing data stays missing.

## Key behavior
- Safe CSV reads handle missing, empty, or malformed snapshots without crashing.
- Unique Streamlit widget keys per region.
- Multiple selections **within** a filter are ANY or ALL; **between** different filter groups are AND.
- No fabricated sector/factor membership, price history, or fundamentals.
- Consistent across Global, USA, India.

## Testing
`python -m pytest tests/test_holdings_workspace.py`

## Compatibility
Retains `render_analysis(region)` and `render_graph(region)` entry points. The older `render_graph` function is now a lightweight delegate to the research workspace, so if you actively use that legacy radial graph, preserve a copy before installing.
