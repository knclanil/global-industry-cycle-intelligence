# global-industry-cycle-intelligence

Streamlit Community Cloud-ready USA sector rotation dashboard. **No database.** Data is downloaded from Yahoo Finance on demand and cached in memory for one hour.

## Deploy from GitHub

1. Create a GitHub repository named `global-industry-cycle-intelligence`.
2. Upload `app.py` and `requirements.txt` to the repository root.
3. In Streamlit Community Cloud, create an app from your repository, set the main file path to `app.py`, and deploy.
4. If the market-data provider rate-limits requests, wait and refresh. No API secrets are required for this prototype.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Dashboard controls

- Sector multiselect with Select All checkbox (uncheck to choose individual sectors).
- Relative time: 1W, 2W, 4W, 1M, 3M, 6M, 12M.
- From Date and To Date controls.
- Four quadrant KPI cards, quadrant filter, rotation map with trails, excess-return bar chart, classification table.

## Calculation

Relative ratio = adjusted sector close / adjusted SPY close. Relative strength = percent change in ratio over selected relative-time lookback. Momentum = percent change in ratio over half the lookback. Quadrants: Leading (+,+), Improving (-,+), Weakening (+,-), Lagging (-,-). This is a custom transparent model, **not** a proprietary RRG formula.

## Data integrity and limitations

Primary-source checks cover OHLC consistency, missing records, duplicate dates, price positivity and large-return warnings. A FAIL blocks classification. **Cross-provider verification is not yet implemented**; passing primary checks is not independent validation. Yahoo Finance can be delayed or rate-limited. Adjusted close is provider-dependent and not guaranteed to equal a verified total-return series. No data is saved to disk.
