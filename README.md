# USA Membership Rank — Direct Replacement

This package provides a **complete regional_rotation_graph.py** (not an installer).
Replace the file of the same name in your repository ROOT, commit and push using GitHub Desktop.

It adds `Final Rank`, `Total Rank`, and `Rank Status` after Ticker **only for USA** in **Knowledge Graph → All verified company memberships**. Ranked rows appear first, and all companies matching the graph/table selection remain present. Open **USA fundamental KPI values and individual ranks** for the five values and their individual ranks.

Ranking inputs: `data/usa_research/fundamental_rankings.csv` on the deployed branch. Missing data shows a warning and rank columns rather than silently hiding the feature.

The source code was built from the prior full Knowledge Graph file in this conversation and cross-checked against the current public `main` table anchor. Because a full live repo checkout and deployment were not possible, REVIEW the GitHub Desktop diff before committing, especially any graph-related changes beyond the new USA ranking block. Do not overwrite newer graph changes unless the diff is limited to the intended insertion.

No network calls, no new data collection, and no changes to India or Global ranking.
