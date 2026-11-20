# Automatic Knowledge Graph refresh — GitHub Desktop setup

This package includes the complete graph Python code from the earlier package **plus** an automatic GitHub Actions workflow and its validation script.

## Install without using a terminal

1. Extract this ZIP.
2. Open **GitHub Desktop**, select `global-industry-cycle-intelligence`, then **Repository → Show in Explorer/Finder**.
3. Copy the extracted files and folders **into that repository root**, merging `scripts`, `tests`, and `.github`. Keep the `.github/workflows/refresh-knowledge-graphs.yml` folder path exactly as shown. Do **not** copy the outer `knowledge_graph_automatic` folder as a nested folder.
4. In GitHub Desktop, check that `.github/workflows/refresh-knowledge-graphs.yml` and `scripts/validate_rotation_graph_cache.py` appear under **Changes**. Enter a commit description, click **Commit to main**, then **Push origin**.
5. On GitHub, open the repository's **Actions** tab, select **Refresh Knowledge Graphs**, and click **Run workflow** (choose `main`). The same workflow will also run automatically on weekdays and after the listed code files change.
6. When the workflow finishes, expand its steps and confirm **Validate membership snapshots and build manifest** is green. It will then commit the generated caches to `main`; Streamlit Cloud should pick up the new commit.

## What is generated

`data/dashboard_cache/rotation_graphs/{global,usa,india}_{1m,3m,6m}_edges.csv`, corresponding signals and other snapshot files, and `manifest.json`.

## Important limits

- The workflow **builds graph snapshots from the market histories and holdings already available to the repository/job**. It does **not** magically populate absent upstream data. If your price/holdings refresh is another job, it must finish before the graph build; otherwise the graphs may remain empty or stale.
- Validation fails on builder errors or missing files and prevents incomplete cache commits. Zero rows are allowed because unavailable source data cannot be fabricated.
- Repository Settings → Actions → General → **Workflow permissions** may need **Read and write permissions** to let this job push cached files. GitHub branch protection may prevent bot pushes; in that case a pull-request workflow or artifact-based deployment is required.
- GitHub Actions scheduled runs use UTC and may be delayed. This workflow runs on weekdays at **11:30 UTC** and also supports manual runs.
- If GitHub refuses the push, inspect the final step's log. If data retrieval or dependencies fail, inspect the build/install log and manifest error.
