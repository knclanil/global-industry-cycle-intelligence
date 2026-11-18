# Usa Factors — Methodology and Data Wiki

## Coverage and instruments

| Instrument / NSE series | Factor proxy |
|---|---|
| IVE | Value |
| IVW | Growth |
| MTUM | Momentum |
| QUAL | Quality |
| USMV | Minimum Volatility |
| IWM | Small Cap |
| VYM | Dividend Yield |

**Benchmark:** SPY. **Source:** Yahoo Finance ETF adjusted closes. These are observable ETF/index proxies, not isolated academic factor returns. ETF holdings and index construction may differ across regions; the same factor label does not guarantee identical exposure. For India, factor index series are price indices and do not include dividends, unlike adjusted ETF prices used elsewhere.

## Exact dashboard calculations

Let P be the instrument adjusted closing price (index close for India), B the benchmark price, and Q=P/B. Relative time chooses L trading sessions: 1W=5, 2W=10, 4W=20, 1M=21, 3M=63, 6M=126, 12M=252. RS(t)=100×(Q(t)/Q(t−L)−1). Momentum(t)=RS(t)−RS(t−M), M=max(2,floor(L/2)). Leading: RS≥0 and momentum≥0; Improving: RS<0 and momentum≥0; Weakening: RS≥0 and momentum<0; Lagging: RS<0 and momentum<0.

Sector/factor performance bars: 100×(P(end)/P(start)−1) minus 100×(B(end)/B(start)−1), in percentage points. Trend line at each date: cumulative factor return minus cumulative benchmark return, both rebased to the first selected trading session. It starts at zero. Date range controls the chart and as-of date; relative time controls RS/momentum lookback. Smooth rotation paths are interpolation for display only, not fabricated market observations.

## Data quality and limitations

Checks flag missing benchmark, nonpositive/duplicate adjusted closes, unavailable factor series, missing benchmark-aligned sessions, stale observations and extreme moves. Missing factor series are omitted; benchmark failure stops calculations. PASS is a structural check, not proof of zero gaps or independent price reconciliation. NSE endpoints may block cloud requests. India factor indices have **no automatic Yahoo factor substitution** without a verified identical index series; only the Nifty 50 benchmark has a known Yahoo symbol (`^NSEI`). Data is fetched on demand, cached for one hour; the scheduled GitHub Action audits USA sectors only. No database. This is descriptive factor proxy rotation, not causal attribution, risk-adjusted factor premiums, or investment advice.
