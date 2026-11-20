# India Quality Rankings: Why the screen was empty

The available `data/india_financials/reference_snapshot.csv` contains 514 companies with point-in-time provider ratios, but no multi-year annual statement histories. The strict multi-year consistency model therefore correctly produced zero **verified** quality ranks. The former UI showed only verified ranks and consequently appeared blank.

## Fix

* India now opens directly on **Company financials**, displaying all available companies and cached ratios.
* A **single-date snapshot comparison / 100** is shown separately, based on observed ratio percentiles. It **is not** a historical consistency score, industry-specific model, valuation, or investment recommendation. Only companies with at least four observed metrics and 60% covered snapshot weight receive a comparative position.
* **Verified consistency ranks** remain separate and require three consecutive annual financial statements with sufficient coverage and stability data; a snapshot is never treated as multi-year history.
* **Intrinsic & Graham** remains separate and cannot be calculated from point-in-time published ratios without statement-derived EPS, equity, shares and historical cash flows.
* The cache token now watches the India CSV and annual company JSON files so newly deployed data invalidates the previous Streamlit result.
* **Source & coverage diagnostics** reports dataset presence, company counts, and annual-statement coverage. If zero records are loaded, check the deployed repository path.

## Deployment

Copy the **contents** of `nightly_build/` into the root of the Streamlit repository (where `app.py` resides). Ensure `data/india_financials/reference_snapshot.csv` is tracked and committed in Git; simply uploading the Python modules is not enough. Keep prior `data/india_holdings` and financial histories.

To verify the imported data:

```bash
python -c "from fundamental_rankings_engine import get_rankings, snapshot_comparison; x=get_rankings('India'); print('companies',len(x),'verified ranked',sum(x.Status=='Ranked'),'snapshot compared',snapshot_comparison(x)['Snapshot comparison / 100'].notna().sum())"
```

At build time, the included 514-company file yielded **514 companies, 0 multi-year ranked, and 509 single-date snapshot comparisons**. These counts refer to the packaged snapshot and can change after data updates.
