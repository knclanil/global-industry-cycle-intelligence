UNIFIED KNOWLEDGE GRAPH — THREE VIEWS, SAME FOUR-COLUMN FORMAT

For Global, USA, India:
ROTATIONS (Leading / Improving / Weakening / Lagging) -> SECTORS -> COMPANIES -> FACTORS

Views:
1. Overview — all sector/factor signals and first 60 companies for readability;
   check "Show every company" to see the entire graph.
2. Sector / Factor — select one sector or factor to see every mapped company
   and each company's other verified sector/factor memberships.
3. Individual Companies — select one company to see its complete verified
   sector/factor connections and the rotation of each underlying index.

The graph layout is identical in all three views. The Global, USA, India pages
use the same render_graph(region) function.

GITHUB DESKTOP INSTALL:
1. Download and extract this ZIP.
2. In GitHub Desktop choose Repository > Show in Explorer / Finder.
3. Copy regional_rotation_graph.py into the ROOT of the repository, replacing
   the existing file. Do not replace app.py.
4. Commit and Push origin in GitHub Desktop.
5. Open Streamlit after redeployment.

REQUIREMENTS:
The existing rotation_graph_evidence.py and generated
 data/dashboard_cache/rotation_graphs/{global,usa,india}_{1m,3m,6m}_{signals,edges}.csv
must already exist. This package only updates the visualization; it does not
regenerate missing data.

Company-to-factor links indicate verified index/portfolio membership, not
independent company-level rotation classifications. Graph inputs must be
validated before interpretation.

Python syntax verified. Live Streamlit runtime not verified.
