"""Presentation helpers for source-labelled Screener consolidated statements.

The source table's labels and supplied observations are preserved. This module
never estimates missing values, changes cash-flow signs, or merges providers.
"""
from __future__ import annotations

import re
import math
import pandas as pd

_PERIOD_RE = re.compile(r"^(?:Mar|Jun|Sep|Dec)\s*['’]?\d{2,4}$|^(?:FY\s*)?20\d{2}$", re.I)


def _period_order(label: str) -> tuple[int, int]:
    text = str(label).strip().replace('’', "'")
    match = re.fullmatch(r"(Mar|Jun|Sep|Dec)\s*'?([0-9]{2,4})", text, re.I)
    if match:
        year = int(match.group(2))
        if year < 100:
            year += 2000 if year <= 79 else 1900
        return year, {'mar': 3, 'jun': 6, 'sep': 9, 'dec': 12}[match.group(1).lower()]
    year = re.fullmatch(r"(?:FY\s*)?(20\d{2})", text, re.I)
    return (int(year.group(1)), 3) if year else (-1, -1)


def _cell(value):
    if value is None or pd.isna(value):
        return 'N/A'
    text = str(value).strip().replace('\u2212', '-').replace('₹', '').replace(',', '')
    if text in {'', '-', '—', 'nan', 'None'}:
        return 'N/A'
    negative_parentheses = text.startswith('(') and text.endswith(')')
    if negative_parentheses:
        text = '-' + text[1:-1].strip()
    # Screener statements are INR crore. Preserve numeric precision at two decimals.
    try:
        n = float(text)
        if math.isfinite(n):
            return f'{n:,.2f}'
    except (ValueError, TypeError):
        pass
    # Respect source text for non-numeric rows; do not turn percentage rows into INR.
    return str(value).strip() or 'N/A'


def prepare_statement(frame: pd.DataFrame | None, periods: int = 8) -> pd.DataFrame:
    """Return a readable statement with original row labels and dated columns.

    Only period-labelled columns are shown; TTM/notes are excluded rather than
    falsely represented as another financial year. A positive period limit
    selects the most recent N observations (chronological order).
    """
    if frame is None or frame.empty or len(frame.columns) < 2:
        return pd.DataFrame()
    period_cols = [c for c in frame.columns[1:] if _PERIOD_RE.fullmatch(str(c).strip())]
    period_cols = sorted(period_cols, key=lambda c: _period_order(str(c)))
    if periods > 0:
        period_cols = period_cols[-periods:]
    if not period_cols:
        return pd.DataFrame()
    columns = [frame.columns[0]] + period_cols
    result = frame.loc[:, columns].copy()
    result.columns = ['Particulars'] + [str(col).strip() for col in period_cols]
    result['Particulars'] = result['Particulars'].astype(str).str.strip()
    result = result.loc[~result['Particulars'].isin(['', 'nan', 'None'])]
    # Preserve all reported rows, including subtotal labels and source percent rows.
    for col in result.columns[1:]:
        result[col] = result[col].map(_cell)
    return result.reset_index(drop=True)


def prepare_source_table(frame: pd.DataFrame | None, periods: int = 8,
                         *, financial: bool = False) -> pd.DataFrame:
    """Normalize Screener tables for display without changing their data.

    Financial and shareholder-period tables select the latest N dated columns.
    Peer comparison preserves all fields and companies instead.
    """
    if frame is None or frame.empty:
        return pd.DataFrame()
    if financial:
        return prepare_statement(frame, periods=periods)
    frame = frame.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    if len(frame.columns) > 1:
        period_cols = [c for c in frame.columns[1:] if _PERIOD_RE.fullmatch(str(c).strip())]
        if period_cols:
            period_cols = sorted(period_cols, key=lambda c: _period_order(str(c)))
            if periods > 0:
                period_cols = period_cols[-periods:]
            frame = frame.loc[:, [frame.columns[0]] + period_cols].copy()
    # Source supplied percentages, ownership counts, P/E and price are NOT INR crore.
    for c in frame.columns:
        frame[c] = frame[c].map(lambda v: 'N/A' if pd.isna(v) or str(v).strip() in ('', 'nan', 'None') else str(v).strip())
    return frame.reset_index(drop=True)
