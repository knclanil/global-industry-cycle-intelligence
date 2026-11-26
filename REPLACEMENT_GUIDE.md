# Replace the entire GitHub repository (aggregate-only edition)

This archive contains the complete application root. It is intended for a **clean replacement**, not an overlay.

1. Create a backup of the old repository/branch before deleting anything.
2. Create a fresh empty GitHub repository (or remove **all tracked files** in the existing repository's working tree, preserving `.git/`).
3. Extract this ZIP and copy the **contents** of `global_industry_cycle_clean/` to the repository root. Ensure `.github/workflows/` and `.gitignore` are copied too.
4. Run `python verify_clean.py`, `python -m pip install -r requirements.txt`, and `streamlit run app.py` locally where feasible.
5. Commit all additions **and deletions** and push to the deployment branch. For an existing repository, `git add -A` stages deletions.
6. In Streamlit Cloud, configure the repository, branch, and entrypoint `app.py`. Check all 13 pages and the market refresh GitHub Action.

The application does not need SEC or MongoDB credentials. Do not copy old secrets into the new repository.

**Note:** A fresh repository eliminates old files from the new repo's history. Replacing the working tree in an existing repository does not erase its historical commits. Do not force-push or rewrite history without a separate review.

**Data caveat:** The archive preserves aggregate market snapshots and existing sector/factor rotation signal snapshots. The knowledge-graph UI is a sector/factor rotation scatter graph; it is not the former company-rich capital network. The scheduled workflow updates market price snapshots; it does not regenerate rotation graph snapshots automatically.
