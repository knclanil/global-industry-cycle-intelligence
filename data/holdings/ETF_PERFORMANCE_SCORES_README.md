# Performance-aware holdings leadership

Add `etf_performance_scores.csv` to this directory with columns:

`portfolio_id,region,performance_score`

Use the **verified** 0–100 performance scores from your existing USA/Global sector and factor rotation models. `region` must be `USA` or `GLOBAL`; portfolio ID must be one of the configured 33 ETFs. Scores must be for the same observation window. Do not fill missing scores with zero.

Ranking formula: per-ETF conviction = min(1, holding weight / 90th-percentile holding weight within ETF). Sector/factor alignment = average(conviction × corresponding ETF performance score) over matched ETFs. If both sides are present, combine 50/50; if only one side is present, use that side. If neither is scored, show neutral 50 and mark `Missing`. Bonus = 10 × ln(1 + distinct ETF count) / ln(1 + universe ETF count), capped at 10; final score capped at 100. USA and Global are separate universes. Holdings change events are informational and do not modify the score.

**Important:** Do not interpret rankings with `Partial` or `Missing` performance data as confirmed leadership. This build does not invent market performance scores.
