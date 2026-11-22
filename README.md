# USA workflow test-command repair — direct replacement

The log `unrecognized arguments: -m unittest discover python ...` is caused by the GitHub Actions step passing THREE unittest invocations in ONE `run:` shell line. This package contains the complete replacement file, with the test commands on separate lines inside a YAML literal block (`run: |`).

## Install — no installer

1. In GitHub Desktop choose **Repository > Show in Explorer**.
2. Open this ZIP and copy its `.github` folder into the ROOT of your repository. Allow Windows to merge folders and **replace** `.github/workflows/usa-company-fundamentals-refresh.yml`.
3. In GitHub Desktop, inspect **Changes**. The workflow file MUST show a change. Look for `run: |` immediately below `- name: Verify offline parsing and joins` and three lines beginning `python -m unittest`.
4. Commit and **Push origin** to `main`.
5. In the GitHub website, open the `main` branch, then `.github/workflows/usa-company-fundamentals-refresh.yml`. Verify the three commands really appear on separate lines. If the file still says `run: python -m unittest ...` then the intended replacement has not been pushed or you are viewing a different branch.
6. In **Actions**, start a NEW run of **USA Company Fundamentals, Quotes and Ranking Refresh** using the `main` branch. Do not click **Re-run jobs** on an old failing run: it can use the workflow from the old commit.

Important: If the live workflow has a different file path, update *that actual workflow file*; merely copying this file will not fix an independently named workflow. See the file path at the top of the failing GitHub Actions run and look at its source commit.

This repairs the command concatenation only. It does not guarantee the test files or live financial data pipeline will pass.
