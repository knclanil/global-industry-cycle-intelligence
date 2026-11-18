# Market data snapshots

The nightly GitHub Action creates `data/market/<dashboard-market>/<ticker>.parquet`, `sources.json`, and `refresh_<region>.json`.
Do not manually edit generated price files. Historical adjusted closes may be revised by providers.

No market data is bundled in the initial ZIP. Run the GitHub Action manually with `region: all` after deployment to bootstrap the repository.
The dashboard uses the legacy live provider only until its first snapshot is available; thereafter it reads stored data without making market-data requests on interactions.

**Caution:** Provider terms and redistribution permissions must be reviewed before committing price histories to a public repository.
