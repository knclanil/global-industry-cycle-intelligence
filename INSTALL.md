# MaketData integration — controlled deployment

This package replaces the Company Financial Research page's **fundamental data read path** with read-only MongoDB retrieval. It does NOT delete old files/workflows until live Atlas retrieval, ranking and Knowledge Graph migration have been verified.

1. Create a backup branch.
2. Copy `maketdata_bridge.py`, `maketdata_ui.py`, `company_financial_research.py` into the repository root.
3. Add `pymongo>=4.6,<5` to `requirements.txt` (retain existing dependencies).
4. Ensure Streamlit Secrets have `MONGODB_URI` and `MONGODB_DATABASE` (never commit them).
5. Run `python -m unittest discover -s tests` for existing tests; copy `test_maketdata_bridge.py` into tests and run it.
6. Deploy and check AAPL/MSFT and an absent ticker; confirm annual/quarterly records and data quality.
7. Do NOT disable or delete old SEC workflows or caches until MongoDB-backed five-KPI rankings and Knowledge Graph are verified in production.

Limitations: This release is a controlled partial migration, not a fully completed repository cleanup. Existing USA five-KPI ranking and Knowledge Graph still consume local generated datasets. Existing collector workflows remain enabled. Live Atlas connection cannot be tested from this environment.
