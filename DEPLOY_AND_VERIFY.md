# MaketData dashboard integration — deployment and verification

## Changes
- Existing Company Financial Research navigation remains unchanged.
- MongoDB financials are now visible in the first tab; existing SEC research retained in the second tab.
- Existing Load company financials button triggers a MongoDB retrieval; an explicit Pull fundamentals button is also provided.
- Test MongoDB connection button executes an Atlas ping without printing credentials.
- MongoDB annual and quarterly record counts, period dates, raw records, and derived ratios are displayed.
- PyMongo is added to requirements.txt.

## Deployment
Replace the existing repository contents with this ZIP's contents (retain GitHub secrets and Streamlit app settings). Commit and push to main. Streamlit should redeploy automatically. The app entrypoint remains app.py.

## Secrets
Streamlit Secrets must contain MONGODB_URI and MONGODB_DATABASE. Do not commit credentials.

## Smoke test
Open app > USA Financial Research > Company Financial Research.
1. Click Test MongoDB connection; expect Connected to MongoDB Atlas.
2. Enter AAPL and click Load company financials; expect MongoDB query completed and annual/quarterly records if present.
3. Enter MSFT and repeat.
4. Enter ZZZZINVALID; expect missing-record notice, not crash.
5. Open Existing SEC Research (legacy) tab to verify previous functionality remains.

## Limitations
No access to your private Atlas or deployed Streamlit secrets was available in this build environment; live database success is not claimed. Existing USA KPI rankings and Knowledge Graph are not yet migrated to MongoDB. Scoring requires comparable validated data and current valuation inputs, so may show N/A. This package fixes the visible Company Financial Research connection, not the broader fundamental-data migration.

## Local validation
`python -m unittest discover -s tests -p 'test_maketdata_bridge.py' -v`
Four unit tests passed and modified Python files compile. Live Streamlit/Atlas integration requires deployment.
