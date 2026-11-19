# SEC configuration and chart fix

This release is based on the previously supplied fast-load full project.

## Changes
- The SEC HTTP client now reads `SEC_USER_AGENT` from environment variables, top-level Streamlit secrets, or `[sec] user_agent` in Streamlit secrets.
- The application displays a non-sensitive SEC identity availability indicator.
- Filing requests distinguish HTTP errors from network failures.
- Historical financial charts sort dates chronologically and show the most recent ten fiscal periods in USD billions.
- Existing cached financial facts, holdings pages, and scheduled refresh workflow are retained.

## Configuration
Streamlit secrets (one option):

```toml
SEC_USER_AGENT = "GlobalIndustryCycleIntelligence/1.0 contact: your-real-email@example.com"
```

GitHub Actions secrets are separate from Streamlit secrets. A configured secret in GitHub Actions does not automatically appear in Streamlit.

## Known limits
The initial cache parsing and company matching may still be slow on large deployments. This update does not add an external international filings or valuation provider, and does not verify live SEC requests.
