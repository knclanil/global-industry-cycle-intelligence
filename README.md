# Independent company-membership table filtering

This update **preserves the previous Knowledge Graph implementation**, including the graph's own Overview / Sector-Factor / Individual Companies views, rotation/sector/factor/company filtering, factor-family deduplication, links and company display caps.

The **All verified company memberships** expander now has *separate* multiselect controls for rotations, sectors, factor families, and companies, with ANY/ALL matching. Those controls only affect the evidence table and CSV export: they do NOT change the Knowledge Graph. Likewise, interacting with the graph filters does not change the table's result.

Select factor `Value` to match all original Value source indexes while preserving their separate source IDs. The optional “Show other memberships of matching companies” checkbox expands the table to all memberships for matched companies after applying rotation constraints. The default only displays matching selected source evidence. Empty selections show the entire original table. This does not modify or regenerate cached data.

## Install using GitHub Desktop

1. Extract the ZIP.
2. Copy `regional_rotation_graph.py` to your repository root, replacing the existing version. Copy `app.py` too **only if** your local app has not yet received the Assets → Sectors → Factors navigation reorder.
3. In GitHub Desktop, commit and push.
4. Optional: run `python -m unittest discover -s tests -v` for the six standalone membership-filter tests.

This package is tested with sample data and syntax checks; it has not been deployed to your Streamlit Cloud app. Back up local changes before overwriting files.
