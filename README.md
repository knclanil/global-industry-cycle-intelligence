# Company → Factor mapping (India Growth)

This update makes an important distinction:

- **Membership:** A company appears in a stored Nifty500 Growth 50 constituent snapshot. Its connection to the **Growth** factor can be drawn.
- **Rotation:** If Nifty500 Growth 50 lacks a valid price-history signal, the membership is shown as **Rotation unavailable**, not artificially assigned Leading/Improving/Weakening/Lagging.

The Graph uses `Rotation → Sector → Company → Factor` wherever validated rotation/sector connections exist. For Growth-only membership without a validated rotation, it draws **Company → Growth** using a neutral gray edge. The existing Growth family visual deduplication is preserved.

## GitHub Desktop installation

1. Copy `rotation_graph_evidence.py` and `regional_rotation_graph.py` next to `app.py`, replacing the existing versions.
2. Commit and Push origin in GitHub Desktop.
3. In GitHub, run **Actions → Refresh Knowledge Graphs → Run workflow** to rebuild the `india_{1m,3m,6m}_edges.csv` snapshots.
4. After its successful publish and Streamlit redeployment, open **India → Individual Companies**, filter by Growth, or view the full graph.

**Requires** the existing `india_index_rotation_expansion.py` file and a current constituent snapshot with rows whose `index_slug` is `nifty500_growth_50`. If the source has no constituent rows, there is no valid company relationship to draw.

## Validation

`python -m pytest -q test_company_factor.py`

This is a targeted patch against the available deduplicated graph module. Compare local differences before overwriting if your main branch has changed further. It has not been tested in a live Streamlit deployment.
