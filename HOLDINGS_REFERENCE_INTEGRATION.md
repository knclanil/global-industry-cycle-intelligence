# BlackRock collector integration — verification notes

Adapted parsing behavior from the uploaded `factor-holdings-intelligence-main (7).zip` reference collectors:
- `scripts/collect_provided_sources_v1_8_1.py`: issuer-effective-date metadata and alternate CSV encodings.
- `scripts/collect_blackrock_v1_8_5.py`: flexible header normalization.

Updated `scripts/refresh_holdings.py` and added regression tests. The USMV fixture is preserved. The 10 newly supplied portfolio IDs are fetched for diagnostics, but not scored pending classification. If a downloaded response lacks a verifiable issuer-declared effective date, it remains rejected; do not infer dates from URL parameters. Missing or failed sources never imply removals.

Run: `python -m pytest -q tests/test_ishares_csv_parser.py tests/test_blackrock_reference_adapter.py`.

**Not live-verified:** The exact BlackRock responses seen by GitHub Actions, successful ingestion of all 28 sources, and deployment to GitHub/Streamlit. If the action still reports missing effective dates, inspect `data/holdings/diagnostics/*.json` (now includes safe metadata labels) to distinguish an alternate endpoint/response from a parsing issue.
