# Four-quadrant regional rotation graph patch

Supports **Global**, **USA** and **India** with the existing `app.py` routing.

- Leading, Improving, Weakening, Lagging based on existing benchmark-relative index signals.
- Display path: quadrant → sector/factor index → company, drawn from qualified source memberships.
- Existing mapping rules and requirements for both sector **and** factor evidence retained.
- Historical snapshots: 1m / 3m / 6m.

## Apply

Copy `regional_rotation_graph.py` to the repository root (replace existing version).
From the repository root apply `git apply engine_and_builder.patch` (copy patch there or reference its path).
Run `python scripts/build_regional_rotation_graphs.py` after the underlying price histories and holdings have been refreshed.
Commit the graph file, both modified Python files, and generated snapshot CSVs under `data/dashboard_cache/rotation_graphs/` if your deployment expects committed snapshots.

Use `python -m compileall -q regional_rotation_graph.py leading_lagging_engine.py scripts/build_regional_rotation_graphs.py` to check syntax. Tests for graph transformation can be run with `pytest tests/test_four_quadrant_graph.py` after copying them to the repository.

**Limitations:** A company may appear in multiple quadrants if it belongs to differently classified index sources. Membership does not prove company momentum, or capital flows. The generator excludes companies without both a qualifying sector and qualifying factor source in the *same* quadrant. This is intentionally conservative. Some quadrants may be empty due to source coverage. This patch does not change market data acquisition or source mappings.

## Unified three-column network (corrected)

**ONE Plotly visualization**, not four panels, lanes, or graphs.

- Left: **exactly four** large nodes — Leading, Improving, Weakening, Lagging.
- Middle: **sector and factor** nodes connected to their rotation category.
- Right: **company** nodes connected to qualifying sector/factor membership.
- Links are color-coded by rotation; sectors and factors have different marker shapes.
- Companies sharing a `company_key` appear **once**, with multiple incoming links.
- The same renderer serves Global, USA and India using their respective snapshots.

The original conservative **sector AND factor** company qualification is retained.
A rotation with no qualified companies still appears on the left; its links are blank.
The graph is not a measurement of company-level relative strength or cash flows.

To apply: replace the root `regional_rotation_graph.py` with the bundled version, apply
`engine_and_builder.patch` if not already applied, rebuild snapshots, commit and deploy.
