# India financial KPI — historical trends

The **Annual / Quarterly Trends** tab uses the *same downloaded consolidated Screener tables* as the seven financial statement tabs at the bottom of the page; switching frequencies performs no extra HTTP calls.

- **Annual:** grouped revenue/operating-profit/net-profit bars, operating/net profit margins, cash flow from operating/investing/financing activities, net cash flow, borrowings/assets/reserves, EPS, ROCE, and shareholding composition where available.
- **Quarterly:** grouped revenue/operating-profit/net-profit, operating and net margins, EPS, quarter-over-quarter and year-over-year revenue and earnings comparisons, and EPS YoY.
- **History control:** 4 / 8 / 12 / 16 / 20 / 30 reporting periods.
- Missing or unreported series display a clearly labelled empty state. Growth comparisons require a real matching quarter (e.g. Jun 2025 vs Jun 2024); missing periods are never silently bridged. Margin calculations require matching source period labels.
- Screener amounts are generally INR crore, EPS is INR per share, and ratios/shareholding are percentages. Investing cash flow is **not** represented as capital expenditure or free cash flow.
- If a company does not provide specific data in the accessible consolidated tables, charts cannot display those series. Live provider requests and their usage restrictions are unchanged.

## Files

- `india_screener_trends.py`: self-contained historical extraction, growth/margin calculations, Plotly charts.
- `india_kpi_intelligence.py`: Trends tab connected to the new module.
- `tests/test_india_screener_trends.py`: data integrity tests.

## Check

```sh
python -m compileall -q india_kpi_intelligence.py india_screener_trends.py
python -m pytest -q tests/test_india_screener_trends.py
```
