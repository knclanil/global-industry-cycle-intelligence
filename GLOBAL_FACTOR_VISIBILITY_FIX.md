# Global Factor visibility fix

The holdings page now always renders USA Factor, USA Sector, Global Factor and Global Sector, even if the deployed snapshot predates Global Factor ingestion. Missing holdings are explicitly marked unavailable, never fabricated. A separate Global Factor leadership section is always visible and explains when its rankings file is absent. Fund tables use descriptive Factor Type / Sector labels and fund titles rather than portfolio IDs.

The five Global Factor sources remain configured in `holdings_intelligence.py`. To populate the new section, deploy the files to the Streamlit branch and run **Verified iShares holdings refresh**. The workflow commits verified snapshots and `global_factor_rankings.parquet` when data are available. The code also avoids prematurely returning when an older snapshot is unchanged but Global Factor ranking or coverage output is missing.
