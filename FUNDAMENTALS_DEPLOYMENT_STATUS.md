# Fundamental Intelligence: deployment and coverage

## Included
- Existing USA/Global holdings universe, SEC XBRL annual financial-statement extraction, historical metrics, provisional sector-relative ranking and official filing links.
- New scheduled SEC collection job (`.github/workflows/fundamentals-refresh.yml`) and checkpointed batch collector (`scripts/refresh_fundamentals.py`).
- SEC company directory is persisted for use by the dashboard; company-facts snapshots are committed to `data/fundamentals/`.
- The dashboard displays last automated refresh status and errors.

## Required configuration
1. In GitHub repository Actions secrets set `SEC_USER_AGENT` to a real descriptive application name and contact email (e.g. `Global Industry Cycle Intelligence admin@yourdomain.example`, replacing the example address with your actual contact).
2. Run the existing holdings refresh workflow first, then manually run `SEC fundamentals refresh`. Scheduled collection runs after holdings refresh on weekdays; the 250-new-issuer limit makes first-time coverage incremental.
3. Commit the generated snapshots through the workflow and redeploy Streamlit. On-demand refreshes on ephemeral Streamlit hosting are **not persistent**.
4. Inspect `data/fundamentals/refresh_status.json` for SEC matching coverage and errors.

## Not implemented / not yet live
- Global issuer coverage outside SEC reporting, commercial market data and valuation, analyst estimates, automated filing text comparisons, AI filing Q&A, filing alerts, and a validated investment-attractiveness ranking require external data sources/credentials and additional development.
- SEC data cannot be downloaded in the artifact-building environment (external network DNS unavailable). No live financial figures are bundled or fabricated.
- A match requires a US country, exact ticker, and sufficiently similar SEC issuer name. Some legitimate matches may be missed; these require verified identifier resolution.
- Current financial scoring is provisional and **not** a complete fundamental ranking. Industry-specific accounting for banks/insurers/REITs needs dedicated models.
