"""FHI market references v2.3.1 | 2026-11-05.
Changelog: fetch a dated market quote and SEC-reported common shares for optional Graham reference.
Market quotes are delayed/third-party; never silently impute missing values.
"""
from datetime import datetime, timezone
import pandas as pd
import streamlit as st


def sec_common_shares(companyfacts):
    """Latest SEC DEI common shares outstanding (point-in-time), with filed date."""
    facts = companyfacts.get('facts', {}).get('dei', {}).get('EntityCommonStockSharesOutstanding', {})
    rows = facts.get('units', {}).get('shares', [])
    valid = []
    for row in rows:
        if row.get('val') is None or float(row['val']) <= 0 or not row.get('end') or not row.get('filed'):
            continue
        # Instant facts only; avoid duplicated historical periods from newer filings.
        if row.get('start'):
            continue
        valid.append(row)
    if not valid:
        return None
    row = max(valid, key=lambda r: (r['end'], r['filed']))
    return {'shares': float(row['val']), 'as_of': row['end'], 'filed': row['filed'], 'source': 'SEC DEI'}


@st.cache_data(ttl=3600, show_spinner=False)
def market_price(ticker):
    """Fetch recent closing price via yfinance; fail closed if unavailable."""
    import yfinance as yf
    symbol = ticker.strip().upper().replace('.', '-')
    history = yf.Ticker(symbol).history(period='10d', auto_adjust=False)
    if history is None or history.empty or 'Close' not in history:
        return None
    close = pd.to_numeric(history['Close'], errors='coerce').dropna()
    if close.empty or close.iloc[-1] <= 0:
        return None
    idx = close.index[-1]
    return {'price': float(close.iloc[-1]), 'as_of': str(idx.date()), 'currency': 'USD', 'source': 'Yahoo Finance via yfinance (unofficial)'}
