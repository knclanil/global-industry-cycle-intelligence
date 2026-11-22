USA financial workflow — distinct test steps fix

Replaces only .github/workflows/usa-company-fundamentals-refresh.yml.
Each unittest command is now its own named GitHub Actions step. No YAML multiline shell needed.

Copy the .github folder into the repository root; commit and PUSH to main.
Verify GitHub main workflow includes names:
  Test USA financial autopilot (separate step)
  Test USA fundamental rankings (separate step)
  Test USA ranking integration (separate step)
Start a NEW workflow run (do not rerun an old run).
If failure still shows 'Verify offline parsing and joins', the run is using a different/old workflow revision.
