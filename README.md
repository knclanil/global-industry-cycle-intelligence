# Knowledge Graph visual deduplication

## Install with GitHub Desktop
Copy `regional_rotation_graph.py` into your repository root, beside `app.py`, replacing the old version. Commit and **Push origin** in GitHub Desktop. The app should redeploy automatically. No cache rebuild is needed because this only changes presentation and filter aggregation.

## Changes
- For **Global**, **USA**, and **India** graphs, indexes labeled `Nifty500 Value 50`, `Nifty200 Value 30`, etc. render as **one Value factor node**. Same for Momentum, Quality, Low Volatility, Alpha, Growth, Dividend Yield, Equal Weight, Small Cap, and Size.
- Exact duplicates of sector labels also share one visual sector node.
- Underlying index-level signals, source IDs, company memberships, and rotation classifications **remain unchanged**.
- A merged family may include original indexes in different rotations; it displays a union of verified company memberships while keeping original index/rotation details in the hover tooltip and data tables.
- Factor filter choices are by family, not duplicated index labels. `ALL` means match each selected family or sector, **not every index within a family**.
- No fabricated links or market classifications are created.

## Validation
`python -m pytest test_dedup.py` (2 local unit tests). Syntax compilation also passed. Live Streamlit deployment has not been run here. The replacement is based on the latest locally available graph module from the earlier package; if you changed the graph code in GitHub afterward, compare before overwriting.
