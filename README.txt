FIX: Global / USA / India Sector x Factor and Financial coverage EmptyDataError

Replace regional_workspace.py at the repository root with this full file.
The replacement is based on the preceding duplicate-key-fix version and preserves unique widget keys.

Why it failed:
  _matrix -> load(region, 'sector_factor_matrix') -> _csv -> pd.read_csv
  If the CSV contains zero bytes or no columns, pandas raises EmptyDataError.

What changed:
  - Missing, 0-byte, or blank CSVs safely return an empty DataFrame.
  - Bad CSV parsing reports a warning rather than crashing the whole Streamlit page.
  - The Sector x Factor view explains how to rebuild missing data.
  - No fabricated sector-factor relationships or financial metrics are added.

Using GitHub Desktop:
  1. Extract ZIP and copy regional_workspace.py into the repo root.
  2. Commit and Push origin.
  3. Check Global > Sector x Factor and Financial coverage.
  4. To populate missing intersections, check data/dashboard_cache/global_sector_factor_matrix.csv
     and run the repository's dashboard cache refresh workflow. Repeat for USA / India as needed.

Important: This prevents the crash; it does not restore missing data.
