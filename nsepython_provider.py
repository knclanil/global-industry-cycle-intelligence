"""Optional NSEPythonServer index-history adapter for hosted Streamlit deployments.

Only authentic provider OHLC rows are accepted; missing data are never imputed.
"""
from datetime import date, timedelta
import pandas as pd


def normalize_index_history(raw: pd.DataFrame, name: str) -> pd.DataFrame:
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        raise ValueError(f'NSEPython returned no index history for {name}')
    data = raw.copy()
    data.columns = [str(c).strip().upper().replace(' ', '').replace('_', '') for c in data.columns]
    def col(*names):
        for n in names:
            key = n.upper().replace(' ', '').replace('_', '')
            if key in data.columns:
                return data[key]
        raise ValueError(f'NSEPython history missing {names[0]} for {name}')
    dates = pd.to_datetime(col('HistoricalDate', 'EOD_TIMESTAMP', 'TIMESTAMP', 'DATE'), dayfirst=True, errors='coerce')
    if isinstance(dates.dtype, pd.DatetimeTZDtype):
        dates = dates.dt.tz_localize(None)
    idx = pd.DatetimeIndex(dates).normalize()
    def price(*names):
        return pd.to_numeric(col(*names).astype(str).str.replace(',', '', regex=False), errors='coerce').to_numpy()
    frame = pd.DataFrame({'Open': price('OPEN', 'EOD_OPEN_INDEX_VAL'),
                          'High': price('HIGH', 'EOD_HIGH_INDEX_VAL'),
                          'Low': price('LOW', 'EOD_LOW_INDEX_VAL'),
                          'Close': price('CLOSE', 'EOD_CLOSE_INDEX_VAL')}, index=idx)
    frame = frame.loc[~frame.index.isna()].sort_index()
    if frame.index.has_duplicates:
        groups = frame.loc[frame.index.duplicated(keep=False)].groupby(level=0)
        if not all(g.eq(g.iloc[0]).all().all() for _, g in groups):
            raise ValueError(f'NSEPython returned conflicting duplicate sessions for {name}')
        frame = frame.loc[~frame.index.duplicated(keep='last')]
    frame = frame.dropna(subset=['Open', 'High', 'Low', 'Close'])
    if len(frame) < 2 or (frame[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
        raise ValueError(f'NSEPython returned insufficient or invalid prices for {name}')
    if ((frame['High'] < frame[['Open', 'Close', 'Low']].max(axis=1)) |
        (frame['Low'] > frame[['Open', 'Close', 'High']].min(axis=1))).any():
        raise ValueError(f'NSEPython returned inconsistent OHLC for {name}')
    frame['Adj Close'] = frame['Close']  # Price index levels, not dividend-adjusted ETF prices.
    frame['Volume'] = 0
    return frame


def history(name: str, start: date, end: date) -> pd.DataFrame:
    """Retrieve in short chunks to limit upstream response sizes and failures."""
    from nsepythonserver import index_history
    pieces = []
    cursor = start
    while cursor <= end:
        finish = min(cursor + timedelta(days=89), end)
        raw = index_history(name, cursor.strftime('%d-%b-%Y'), finish.strftime('%d-%b-%Y'))
        if isinstance(raw, pd.DataFrame) and not raw.empty:
            pieces.append(raw)
        cursor = finish + timedelta(days=1)
    if not pieces:
        raise ValueError(f'NSEPython returned no observations for {name}')
    frame = normalize_index_history(pd.concat(pieces, ignore_index=True), name)
    frame = frame.loc[pd.Timestamp(start):pd.Timestamp(end)]
    if len(frame) < 2:
        raise ValueError(f'NSEPython returned insufficient requested history for {name}')
    frame.attrs['source'] = 'NSEPythonServer (Nifty Indices)'
    return frame
