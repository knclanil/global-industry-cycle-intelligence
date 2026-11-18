# 3D Market Knowledge Graph

The Global Capital Intelligence Network page now displays an interactive, dark-background 3D force-directed graph inspired by the supplied reference image. Node category colors are distinct from market-status colors. The view supports mouse rotation, zoom, node focus, search, category filters, and expanding/collapsing group nodes.

**Data semantics:** Edges mean a verified market price series belongs to a named source category. The graph does not claim causal market relationships, capital flows, ETF holdings, or company exposures. Company and holdings nodes are excluded. Existing holdings leadership pages and calculations remain untouched.

**Deployment:** Copy the project files to your repository and deploy as before. The visualization loads Three.js, SpriteText and 3d-force-graph from public unpkg CDN; browser network access to that CDN is required. If blocked, the component displays an explanatory error. This has not been browser-tested against the live Streamlit app.

**Controls:** Double-click a category or source group to expand/collapse, click a node to inspect, drag to rotate, scroll to zoom, search by name/ticker, or use Fit graph and Reset view.
