# Multi-select filters on all Knowledge Graph views + remove old Leading & Lagging page

Copy **these three files** to the root folder of your existing GitHub repository, replacing the existing files:

- `app.py` — removes only the **Leading & Lagging Companies** navigation page and route. It does **not** remove the four Leading/Improving/Weakening/Lagging rotation categories inside graphs.
- `regional_rotation_graph.py` — gives **Overview**, **Sector / Factor**, and **Individual Companies** the same multi-select controls for rotations, sectors, companies, and factors on all three regions (Global, USA, India). Selecting filters removes unrelated nodes and displays verified matching memberships.
- `capital_network.py` — maintains the latest six-column **Global → Rotation → Country → Sector → Company → Factor** network, direct Global memberships, and multi-value country/rotation/sector/company/factor selection.

## Install with GitHub Desktop

1. Extract the ZIP.
2. GitHub Desktop → Repository → Show in Explorer / Finder.
3. Copy these three Python files into the repository root and choose **Replace**.
4. In GitHub Desktop, review **Changes**, commit `Enable multi-select on all graphs and remove legacy page`, then **Push origin**.
5. Open the Streamlit app after it redeploys. It uses existing graph snapshots; no new builder is included in this package.

## Filter rules

- Empty selections mean **no restriction** for that category.
- Within one category, multiple choices match **ANY** of the chosen values.
- Between rotation, company, and selected sector/factor criteria, the constraints are intersected.
- The **ANY / ALL** control applies to selected sector/factor memberships.
- Once a filter is active, unrelated sectors/companies/factors are removed from the graph (selected empty sector nodes may remain without made-up links).
- Selecting a company retains all its *verified* sector and factor memberships, including relationships across different rotation classes.
- With no selection, the overview remains broad and uses a company display cap for readability; checkbox allows showing all.

**Dependencies:** Existing `rotation_graph_evidence.py`, generated signal/edge snapshots, and application modules must already be in your repo. No data is invented for countries without verified company memberships. Existing GitHub Actions scripts remain unchanged. Full live Streamlit deployment has not been performed here; Python syntax validation passed.
