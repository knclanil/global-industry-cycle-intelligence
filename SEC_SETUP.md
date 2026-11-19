# SEC Fundamentals — Required GitHub setup

This repository contains the complete Streamlit project and the SEC fundamentals refresh workflow. The workflow already passes `secrets.SEC_USER_AGENT` into the Python process. **The secret must be created by the repository owner; it cannot be supplied in the ZIP.**

1. In GitHub open **Settings → Secrets and variables → Actions → New repository secret**.
2. Set name `SEC_USER_AGENT`; value should be `GlobalIndustryCycleIntelligence/1.0 contact: YOUR_REAL_EMAIL` (replace with a real address).
3. Open **Actions → SEC fundamentals refresh → Run workflow** and choose a limit (default 250).
4. Run the holdings refresh first if the fundamentals script reports that the holdings snapshot is missing.
5. Inspect `data/fundamentals/refresh_status.json` and the job logs for verified coverage and errors.

The first run will not instantly cover every issuer. SEC coverage does not include every global company, and this project does not yet provide complete international filings or live valuation data. Do not interpret missing financial data as a score of zero.

Deploy by placing the **contents of `nightly_build/` at the repository root** (so `app.py`, `requirements.txt`, `.github/workflows/`, `scripts/` and `data/` are at root).
