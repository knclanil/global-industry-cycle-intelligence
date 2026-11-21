# Global Capital Network — connected model (GitHub Desktop)

## Installation (no command line required for deployment)

1. Extract this ZIP.
2. In GitHub Desktop choose **Repository → Show in Explorer/Finder**.
3. Copy **both** `capital_network.py` and `capital_network_model.py` into the **root** of `global-industry-cycle-intelligence`, beside `app.py`. Replace the old `capital_network.py`.
4. In GitHub Desktop, **Commit to main**, then **Push origin**.
5. Open Streamlit → Capital Network. The existing `app.py` should call `render_capital_network()`; this package does not overwrite `app.py` or unrelated dashboards.

## What it fixes

- The GLOBAL node always links to each **visible rotation**. Every country links to its own verified country ETF quadrant. There are no isolated Global roots.
- All verified paths use adjacent columns only: **Global → Rotation → Country → Sector → Company → Factor**.
- One canonical backend relationship table stores each evidence path with source-scoped IDs and provenance. Distinct company memberships are not merged by ticker alone across regions.
- Multiple filters (rotation, country, sector, factor, company) with **Any/All** matching; unrelated records vanish when filtering.
- Global-direct memberships use their own explicit **Global scope → Global direct** branch, not a fabricated country classification.
- Every verified graph line has consistent stroke thickness. Company tickers are shown for readable small selections.
- Sector-less factor membership is presented using a clearly labelled **Sector not verified** gap and dashed UNVERIFIED visual connectors. This is a display scaffold, **not evidence of a sector holding**. Factor-only evidence is retained.
- Country-only nodes are still visible if sector/company data for that country does not exist; this does **not** invent country-to-sector links.
- The model displays **Global rotation breadth** as a clearly disclosed equal-weighted 0–100 country classification indicator. It is **not** a benchmark return, measured capital flow, or market-cap-weighted global strength score. Missing countries are excluded and coverage is shown.

## Important limits

Current source snapshots, based on the available repository implementation, contain verified sector/company constituent membership for **USA, India, and a separate Global-direct scope**. **Other countries have a country ETF rotation but no verified country-scoped sectors/companies** until constituent datasets are supplied. The chart cannot truthfully show Country → Sector for those countries yet.

Existing GitHub Actions workflows should continue producing:

- `data/dashboard_cache/rotation_graphs/country_{1m,3m,6m}_rotations.csv`
- `data/dashboard_cache/rotation_graphs/{global,usa,india}_{1m,3m,6m}_signals.csv`
- `data/dashboard_cache/rotation_graphs/{global,usa,india}_{1m,3m,6m}_edges.csv`

The graph uses those existing caches. If a cache is missing, the page shows partial coverage and diagnostics rather than inventing relationships.

## Validation

Tests included at `tests/test_capital_network_model.py` (four passing using synthetic evidence). Run locally with:

```bash
python -m pytest tests/test_capital_network_model.py -q
```

**Not deployed or end-to-end tested against your live Streamlit environment.** Verify after pushing and monitor deployment logs.

## Weakening quadrant visibility patch

All four rotation nodes now appear in the unfiltered Capital Network, even if the country-rotation snapshot contains no countries classified as Weakening. An empty rotation node has **no fabricated links**. Hovering explains why it has no countries. A country-count caption displays each quadrant's count. When the user selects filters, unrelated rotation nodes disappear as requested.

**Important:** The country rotation file determines actual country membership. A Weakening *sector* or *factor* does not make the enclosing country Weakening. No country classifications have been changed by this patch.
