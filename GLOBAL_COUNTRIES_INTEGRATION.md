# Global Countries integration

The **Global** navigation group now contains **Countries**, **Sectors**, **Factors**, and **Sector · Factor · Holdings**. The Countries route continues to use the existing `country_market_data` dashboard, preserving the original country performance, rotation, and relative-strength views.

The global materialized company directory additionally retains the verified `country` value from iShares holdings, if supplied. Rebuild `data/dashboard_cache/` with `python scripts/build_dashboard_cache.py` or the existing GitHub Actions snapshot builder. The Global regional analysis page then offers a country filter for company-level data. The global knowledge graph can show country-to-company links for companies with verified domicile; it does not infer country from a ticker or ETF. The country filter does not recalculate the global index totals or market-performance series.

USA, India, and existing financial pages are not changed.
