## Architecture and operation

GitHub Actions downloads available market data, calculates market-relative sector indicators, and discovers metadata from explicitly configured official RSS feeds. GitHub stores Parquet, JSON and Markdown files. Streamlit reads these files; no database, server-side credentials or paid LLM is required.

### Update data

Run `python scripts/collect_prices.py`, then `python scripts/analyze.py`, then `python scripts/monitor_publishers.py`. The GitHub workflow runs on weekdays and can be triggered manually. Individual data-source failures are reported and previous files are preserved when possible.

### Research policy

Store publication titles, publisher, original URL, dates and verified notes. Do not store full copyrighted articles. Preserve the distinction between original reported facts, forecasts, analytical hypotheses and market signals. Do not overwrite a historical forecast when it is revised.
