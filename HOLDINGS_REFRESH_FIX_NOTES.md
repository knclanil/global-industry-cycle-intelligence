# Holdings refresh parser — USMV CSV fixture fix

- Parses the uploaded iShares USMV CSV via `csv.reader`, including quoted metadata dates, header after preamble, and trailing copyright text.
- Validates `Fund Holdings as of` from the document itself, not from the request URL.
- Parses equity rows only; preserves issuer and weight validation.
- On HTTP/format failure writes safe response metadata to `data/holdings/diagnostics/<portfolio_id>.json`; GitHub Actions uploads diagnostics as an artifact.
- Scheduled workflow exits successfully on upstream source failures but **does not create or overwrite rankings** unless every configured ETF is verified. Set `HOLDINGS_STRICT=1` to return a nonzero exit code when diagnosing.
- Ten additional portfolio IDs remain in `data/holdings/pending_sources.json` until category verification. They are not silently assigned to factor or sector rankings.
- The uploaded USMV CSV fixture tests verify 179 table rows, 174 equity rows, and 2026-11-17 holdings date.

**Limit:** This validates the supplied CSV, not the live BlackRock API response. If the API returns HTML, a redirect, or a different export format, the workflow will skip updating rankings and produce diagnostics rather than claim success.
