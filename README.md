# India dashboard navigation cleanup

This package contains only `app.py`, preserving the existing Knowledge Graph and financial pipeline code.

## India sidebar after update
1. India Asset Flow
2. India Sector
3. India Factors

The following *sidebar entries* are removed from INDIA only:
- India Analysis (Sector · Factor · Holdings)
- India Sector & Factor Holdings (India Holdings Explorer)
- India Overlap & Leadership
- India Sector & Factor Financials

No data, refresh workflows or analytical modules are deleted. The Company Financials section, Knowledge Graphs, Global, USA, and other research sections remain unchanged. India financial research and any Investment Opportunities tab added to `india_financial_ui.py` is not removed from source code, but its old navigation entry is hidden. The user can choose later where to expose the consolidated opportunity screener.

## Installation
1. Extract ZIP.
2. In GitHub Desktop, Repository > Show in Explorer.
3. Back up existing root `app.py` if desired.
4. Replace root `app.py` with this file.
5. Commit and Push origin.

## Test
`python -m py_compile app.py` succeeds. Live Streamlit navigation not tested.

## Important
This patch assumes that `app.py` matches the previously inspected app navigation structure. Before replacement, check GitHub Desktop's diff to ensure any newer custom changes in the original app.py are not overwritten. It does not overwrite `regional_rotation_graph.py` or financial modules.
