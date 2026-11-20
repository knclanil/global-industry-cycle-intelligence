# Fundamental Quality Model V3 — Release notes

This update replaces the prior 85% ratio percentile / 15% stability calculation on the **Fundamental Quality & Consistency** page. It does not modify market-based Leading & Lagging or the original USA/Global ETF leadership formulas.

Changes:
1. Fixed five-domain business quality model: 25% profitability, 20% financial strength, 20% multi-year growth, 20% cash flow, 15% historical consistency. Financial businesses have a separate provisional 35/25/25/15 domain framework.
2. Adds Revenue CAGR, internally derived EPS CAGR, FCF margin, positive FCF years, FCF CAGR, cash conversion and historical operating evidence from verified annual statement data.
3. Uses industry/region-specific percentiles with a minimum of five peers per metric. Missing domains are not renormalized into inflated 100-point scores. Only verified 3+ year histories can be ranked.
4. Correctly preserves single-period India reference data in a **snapshot-only comparison**. Without annual financial statement JSONs, Indian companies will display, but verified historical rankings and statement-derived Graham/DCF remain unavailable.
5. Rewrites the methodology wiki and updates the UI methodology table to the real V3 weights and dimensional scores. Valuation stays separate from quality.

## Validation

Targeted tests: 17 passed (ranking engine, missing-data protection, bank branch, previous regression tests and valuation tests). Compilation passed. End-to-end Streamlit rendering is **not** validated here; the broader project's all-tests run stops during discovery at `tests/test_parallel_network.py` because the test environment's `streamlit` stub lacks `cache_data`.

## Data coverage warning

Current packaged India reference file contains 514 company snapshots; no annual statement JSON files were in `data/india_financials/companies/` in the source package. This release **cannot invent** five-year histories from a single-period snapshot; it shows 514 company snapshots and 509 preliminary comparison scores, but zero verified multiyear India ranks with the included data. Run the India financial statement refresh workflow and ensure its verified annual snapshots are committed to populate historic rankings. Provider restrictions may limit coverage.

## Deployment

Extract the `nightly_build` directory and copy its **contents** into your repository root. Preserve your live `data` folders, including NSE history and SEC caches, rather than overwriting them with older templates. Push and restart Streamlit. The Wiki page is included as a Markdown file but is not published to GitHub Wiki automatically.
