# Knowledge Graph → Verified Membership Table synchronization

## What this fixes

The **All verified company memberships** table can now use the **exact same company cohort** as the graph above without changing how the graph works.

Inside that section, choose **Company table source**:

1. **Companies displayed in graph** (default): exactly the company nodes drawn after the 60/100-company display limit. All of their verified sector/factor memberships appear in the table, including source memberships with other rotations.
2. **All companies matching graph filters**: includes the entire matching company cohort before the graph's display limit.
3. **Independent company search**: the original standalone table filters, ignoring graph selections.

For either graph-based option, enable **Further narrow the graph companies using table filters** only if you want to apply additional table-only criteria. Otherwise the table lists all verified evidence for those companies; the graph is unaffected.

The graph's selections and chart rendering logic are unchanged. The new behavior only chooses which **company identities** are included in the table. It does not reduce the graph or change underlying membership snapshots.

## Installation using GitHub Desktop

Copy `regional_rotation_graph.py` beside `app.py` in the repository root, replacing the old file. Commit and push via GitHub Desktop. No cache rebuild is required. Existing `rotation_graph_evidence.py`, data snapshots, and GitHub Actions workflows are unchanged.

## Verification

- Select the graph's Lagging rotation plus Growth, Quality and Value factors; choose Any or All.
- Open **All verified company memberships · table filters**.
- Leave **Companies displayed in graph** selected. The table must contain the exact **distinct company identities** displayed in the graph; each company can have several evidence rows.
- Switch to **All companies matching graph filters** to see companies omitted from the graph only because of its 60/100-company visual limit.
- Choose **Independent company search** for separate company membership queries.

Synthetic unit tests passed (3/3), and Python syntax compilation passed. This patch has not been deployed or tested in the live Streamlit Cloud application. If `regional_rotation_graph.py` has been edited more recently in your repository, compare the diff before replacing it.
