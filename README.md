# Global Industry Cycle Intelligence — Aggregate Edition

Only **Global, USA, and India** market-level **assets, sectors, factors** and their **index-level knowledge graphs** are included. Global Countries is retained.

**Removed:** issuer/company records, individual-company views, company holdings, fundamental statements, SEC collectors, MongoDB fundamental bridge, individual ticker screeners, constituent membership and company-to-factor graph edges.

Index/ETF symbols are retained because they represent **asset classes, sector ETFs, factor ETFs, country ETFs and benchmark indices**, not individual company securities.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Refresh market-level price snapshots

Use the retained GitHub Actions **Incremental market data refresh** workflow. It writes only `data/market/` index/ETF snapshots. No SEC, issuer financial, holdings, or company collectors are included.

## Navigation

Knowledge Graphs: Global, USA, India (sector/factor rotation evidence only).
Global: Countries, Asset Flow, Sectors, Factors.
USA: Asset Flow, Sectors, Factors.
India: Asset Flow, Sectors, Factors.
Wiki: Market Intelligence Wiki (preserved market methodology documentation).

## Deployment warning

To actually remove old files from an existing GitHub repository, replace its tracked content with this edition **and commit the deletions**. Uploading only the files in this archive without deleting old files will leave old company/SEC data in Git history and possibly in the current branch. Git history is not rewritten by this archive; history cleanup is a separate destructive operation requiring coordination.
