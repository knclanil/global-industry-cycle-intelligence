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

## Three-column layout (updated)

The default view now shows **all four quadrants at once**. The graph flows **left to right**:

`Rotation (Leading / Improving / Weakening / Lagging) → Sector and Factor → Company`.

Each rotation has its own horizontal lane, avoiding unintended links between different quadrant signals. A category selector can optionally focus on a single lane. Global, USA, and India all use the same layout and their respective snapshots. Companies are still required to have both sector and factor membership evidence within a lane.
