# Global Capital Intelligence Network — 2D Orbital Knowledge Graph

## Design and structure

The central **GLOBAL** node connects to **Countries**, **Global Sectors**, and **Global Factors**. Countries expand to asset classes (Equity, Bonds, Cash where data exists); Equity expands to sector/factor strategies and related ETFs. Bond and Cash categories expand to their verified related ETFs. Global Sectors and Global Factors have separate global ETF branches. Companies and individual ETF holdings are **excluded from the graph**.

## Interaction and display

The current graph implementation is **2D SVG**, not Three.js or 3D. Nodes have visible labels, performance scores inside circles where available, and neutral colors. Higher performance is intended to produce larger circles and shorter parent-orbit distance. Clicking expands/collapses branches. Search, Fit View, Expand All, Collapse, zoom, and pan are available. The viewport-aware orbital renderer attempts to adapt on browser resize and branch changes.

**Interpretation:** Orbital lines express hierarchy/verified category membership, not inferred money flows. Cross-branch relationships must be verified; the supplied renderer does not establish arbitrary cross-links. Fit View is designed to preserve circle geometry; dense Expand All layouts may still require zoom/pan and may have label collisions. A complete collision-avoidance engine and verified live browser test have **not** been demonstrated.

## Performance, availability and data integrity

Performance scores should originate in the existing country, asset, sector and factor calculations; do not fabricate scores for missing data. Structural nodes have no implied market performance. USA and Global ETF categories are distinct. Verify fund titles, category assignments, and date consistency before display. ETF presence is not evidence of company-level capital inflows.
