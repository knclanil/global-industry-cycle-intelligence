# Hide unrelated nodes when filters are selected

Replacement files for your existing GitHub Desktop repository:

- `capital_network.py` — Capital Network, Global → Country → Sector → Company → Factor.
- `regional_rotation_graph.py` — Global, USA, India Knowledge Graphs, Rotation → Sector → Company → Factor.

## Install (GitHub Desktop)

1. Download and extract the ZIP.
2. In GitHub Desktop choose **Repository → Show in Explorer/Finder**.
3. Copy the two `.py` files into the **root** of your repository, alongside `app.py`, replacing the existing files.
4. In GitHub Desktop, **Commit to main** and **Push origin**.
5. Let Streamlit redeploy. No cache rebuild is needed if your current `*_signals.csv` and `*_edges.csv` already work.

## How filtering behaves

- With no filters, keep the overview and the 20 tracked country nodes in the Capital Network.
- Once you select country, rotation, sector, factor, or company, **only matching companies, their verified sector/factor connections, the relevant country node(s) and Global root** remain. Unrelated branches disappear rather than fading.
- Multiple values in the Country, Rotation, and Company filters select **any of those values**. Sector / Factor `Any selected` or `All selected` controls whether companies must match at least one or every chosen source. **Different filter categories are combined**: a company must meet every selected category.
- If a selected sector, factor, or country has no verified company connections, keep the selected node as an explanation; do not invent companies. Other unrelated nodes disappear.
- Knowledge Graph focused views hide rotation nodes with no visible source connections. Overview remains unfiltered.
- Global continues to have its own direct global-sector, global-company and global-factor connections in Capital Network.
- The underlying data and CSV snapshots are not modified.

## Verification

Run `python test_strict_filter.py` from the extracted directory (requires pandas and plotly; Streamlit is stubbed when absent). These are targeted logic tests, not a live deployment test.
