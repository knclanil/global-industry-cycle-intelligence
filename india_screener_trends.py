"""Historical charts from already-retrieved Screener consolidated tables.

No network calls. Amounts retain the source's INR crore basis, except
percentage and per-share series. Missing data is never replaced by zero.
"""
from __future__ import annotations

import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from india_screener_statements import _period_order

PATTERNS = {
    'Revenue': [r'^Sales\s*\+?$', r'^Revenue(?: from Operations)?\s*\+?$'],
    'Expenses': [r'^Expenses\s*\+?$', r'^Total Expenses\s*\+?$'],
    'Operating profit': [r'^Operating Profit\s*\+?$'],
    'Other income': [r'^Other Income\s*\+?$'],
    'Profit before tax': [r'^Profit before tax\s*\+?$', r'^Profit Before Tax\s*\+?$'],
    'Net profit': [r'^Net Profit\s*\+?$'],
    'EPS': [r'^EPS in Rs\.?\s*\+?$', r'^EPS\s*\+?$'],
    'OPM': [r'^OPM\s*%?\s*\+?$'],
    'Tax rate': [r'^Tax\s*%?\s*\+?$'],
    'Borrowings': [r'^Borrowings\s*\+?$'],
    'Reserves': [r'^Reserves\s*\+?$'],
    'Share capital': [r'^Equity Capital\s*\+?$', r'^Share Capital\s*\+?$'],
    'Total assets': [r'^Total Assets\s*\+?$'],
    'Fixed assets': [r'^Fixed Assets\s*\+?$'],
    'Investments': [r'^Investments\s*\+?$'],
    'Cash operations': [r'^Cash from Operating Activit(?:y|ies)\s*\+?$'],
    'Cash investing': [r'^Cash from Investing Activit(?:y|ies)\s*\+?$'],
    'Cash financing': [r'^Cash from Financing Activit(?:y|ies)\s*\+?$'],
    'Net cash flow': [r'^Net Cash Flow\s*\+?$'],
    'ROCE': [r'^ROCE\s*%?\s*\+?$'],
    'Debtor days': [r'^Debtor Days\s*\+?$'],
    'Inventory days': [r'^Inventory Days\s*\+?$'],
    'Cash conversion cycle': [r'^Cash Conversion Cycle\s*\+?$'],
    'Promoters': [r'^Promoters\s*\+?$', r'^Promoter Group\s*\+?$'],
    'FIIs': [r'^FIIs\s*\+?$', r'^Foreign Institutions\s*\+?$'],
    'DIIs': [r'^DIIs\s*\+?$', r'^Domestic Institutions\s*\+?$'],
    'Public': [r'^Public\s*\+?$'],
}

ANNUAL_TABLES = {'Profit & Loss', 'Balance Sheet', 'Cash Flows', 'Ratios'}


def _parse_cell(value):
    if pd.isna(value):
        return np.nan
    raw = str(value).strip().replace(',', '').replace('₹', '').replace('%', '')
    if raw in {'', '-', '—', 'nan'}:
        return np.nan
    if raw.startswith('(') and raw.endswith(')'):
        raw = '-' + raw[1:-1]
    try:
        return float(raw)
    except (TypeError, ValueError):
        return np.nan


def _row_series(frame, patterns):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.Series(dtype=float)
    labels = frame.iloc[:, 0].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    for pattern in patterns:
        matched = labels.str.contains(pattern, case=False, regex=True, na=False)
        if matched.any():
            row = frame.loc[matched].iloc[0]
            return pd.Series({str(k): _parse_cell(row[k]) for k in frame.columns[1:]}, dtype=float).dropna()
    return pd.Series(dtype=float)


def series_from(frame, name, *, frequency='Annual') -> pd.Series:
    """Extract a reported source row with proper chronological labels."""
    raw = _row_series(frame, PATTERNS[name])
    if raw.empty:
        return raw
    valid = {label: float(value) for label, value in raw.items()
             if _period_order(label) != (-1, -1)}
    if not valid:
        return pd.Series(dtype=float)
    # Reject TTM, notes, malformed and off-frequency periods. In Screener
    # annual tables 'Mar YYYY' denotes FY, while quarters use all month labels.
    if frequency == 'Quarterly':
        valid = {k: v for k, v in valid.items() if re.match(r'^(Mar|Jun|Sep|Dec)\s*[\'’]?\d', str(k), re.I)}
    return pd.Series(valid, dtype=float).sort_index(key=lambda idx: idx.map(_period_order))


def pct_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Ratio only for exactly corresponding reporting periods."""
    a, b = numerator.align(denominator, join='inner')
    if a.empty:
        return pd.Series(dtype=float)
    b = b.replace(0, np.nan)
    values = (a / b * 100).replace([np.inf, -np.inf], np.nan)
    return values.dropna()


def growth_pct(series: pd.Series, periods: int) -> pd.Series:
    """Compare only real consecutive reporting quarters/years, not list positions.

    Quarterly data must have exactly 3/12 months between adjacent/comparison
    points; an absent quarter must not be silently skipped.
    """
    if series.empty:
        return pd.Series(dtype=float)
    freq_months = 3 if periods in (1, 4) else 12
    # caller passes 1 or 4 for quarterly; annual uses 0
    if periods == 0:
        freq_months, offset = 12, 1
    else:
        offset = periods
    timestamps = {}
    for label, value in series.items():
        y, m = _period_order(str(label))
        if y > 0 and np.isfinite(value):
            timestamps[y * 12 + m] = (str(label), float(value))
    results = {}
    for time_key, (label, value) in timestamps.items():
        previous = timestamps.get(time_key - freq_months * offset)
        if previous and previous[1] > 0:
            results[label] = (value / previous[1] - 1) * 100
    return pd.Series(results, dtype=float)


def _chart(title, data, *, unit='₹ crore', max_periods=12, bars=False):
    import streamlit as st
    fig = go.Figure()
    has = False
    for label, series in data:
        series = series.dropna().iloc[-max_periods:] if not series.empty else series
        if series.empty:
            continue
        has = True
        params = dict(x=series.index.astype(str).tolist(), y=series.values, name=label)
        if bars:
            fig.add_trace(go.Bar(**params))
        else:
            fig.add_trace(go.Scatter(**params, mode='lines+markers', connectgaps=False))
    if not has:
        st.info(f'{title}: no reported observations available.')
        return
    from research_theme import PLOTLY_LAYOUT
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(title=title, height=318,
                      margin=dict(l=20, r=12, t=52, b=37),
                      barmode='group', hovermode='x unified',
                      yaxis_title=unit,
                      legend=dict(orientation='h', y=-.26),
                      xaxis=dict(type='category'))
    st.plotly_chart(fig, use_container_width=True)


def render_screener_trends(tables: dict):
    """All financial plots are sourced from in-memory Screener tables."""
    import streamlit as st
    mode = st.radio('Reporting frequency', ['Annual', 'Quarterly'], horizontal=True,
                    key='india_kpi_screener_trends_frequency')
    max_periods = st.select_slider('History', options=[4, 8, 12, 16, 20, 30], value=12,
                                   key='india_kpi_screener_trends_window')
    if mode == 'Quarterly':
        q = tables.get('Quarterly Results')
        if q is None or q.empty:
            st.warning('No quarterly consolidated results were supplied by Screener.')
            return
        get = lambda name: series_from(q, name, frequency='Quarterly')
        rev, op, profit, eps = (get(k) for k in ['Revenue','Operating profit','Net profit','EPS'])
        opm = get('OPM')
        if opm.empty:
            opm = pct_ratio(op, rev)
        net_margin = pct_ratio(profit, rev)
        st.caption('Individual reported quarters only · ₹ crore except EPS and percentages. '
                   'QoQ and YoY require matching calendar quarters; missing periods are not filled.')
        a, b = st.columns(2)
        with a: _chart('Quarterly revenue and earnings', [('Revenue',rev),('Operating profit',op),('Net profit',profit)],max_periods=max_periods,bars=True)
        with b: _chart('Quarterly margins', [('Operating margin',opm),('Net margin · calculated',net_margin)],unit='%',max_periods=max_periods)
        a, b = st.columns(2)
        with a: _chart('Quarterly EPS',[('EPS',eps)],unit='₹ per share',max_periods=max_periods)
        with b: _chart('Revenue growth', [('Quarter over quarter',growth_pct(rev,1)),('Year over year',growth_pct(rev,4))],unit='%',max_periods=max_periods)
        a, b = st.columns(2)
        with a: _chart('Net profit growth', [('Quarter over quarter',growth_pct(profit,1)),('Year over year',growth_pct(profit,4))],unit='%',max_periods=max_periods)
        with b: _chart('EPS growth', [('Year over year',growth_pct(eps,4))],unit='%',max_periods=max_periods)
        st.caption('Quarterly balance-sheet and cash-flow series are omitted because Screener’s standard annual tables do not establish individual quarterly observations.')
        return

    pl = tables.get('Profit & Loss'); bs = tables.get('Balance Sheet')
    cf = tables.get('Cash Flows'); ratios = tables.get('Ratios')
    g = lambda table, name: series_from(table,name)
    rev, op, net, eps = (g(pl,k) for k in ['Revenue','Operating profit','Net profit','EPS'])
    opm = g(pl,'OPM')
    if opm.empty: opm = pct_ratio(op,rev)
    net_margin = pct_ratio(net, rev)
    borrow, assets, reserves = (g(bs,k) for k in ['Borrowings','Total assets','Reserves'])
    ops, investing, financing, net_cf = (g(cf,k) for k in ['Cash operations','Cash investing','Cash financing','Net cash flow'])
    roce = g(ratios,'ROCE')
    st.caption('Screener consolidated annual reporting periods · financial amounts ₹ crore. '
               'Investing cash flow is not treated as capital expenditure or free cash flow.')
    a,b=st.columns(2)
    with a: _chart('Revenue and earnings', [('Revenue',rev),('Operating profit',op),('Net profit',net)],max_periods=max_periods,bars=True)
    with b: _chart('Profitability margins',[('Operating margin',opm),('Net margin · calculated',net_margin)],unit='%',max_periods=max_periods)
    a,b=st.columns(2)
    with a: _chart('Cash flow activities',[('Operating',ops),('Investing',investing),('Financing',financing),('Net cash flow',net_cf)],max_periods=max_periods,bars=True)
    with b: _chart('Borrowings, assets and reserves',[('Borrowings',borrow),('Assets',assets),('Reserves',reserves)],max_periods=max_periods)
    a,b=st.columns(2)
    with a: _chart('Earnings per share',[('EPS',eps)],unit='₹ per share',max_periods=max_periods)
    with b: _chart('Return on capital employed',[('ROCE',roce)],unit='%',max_periods=max_periods)
    # Ownership can be annual or quarterly, depending on the source table.
    ownership = tables.get('Shareholding Pattern')
    if isinstance(ownership,pd.DataFrame) and not ownership.empty:
        st.markdown('#### Shareholding trends')
        components = [(name,g(ownership,name)) for name in ('Promoters','FIIs','DIIs','Public')]
        _chart('Shareholding pattern',components,unit='% of shares',max_periods=max_periods)
    st.caption('Reporting periods and accounting bases are source-labelled. Calculated margins require exact matching period labels; N/A is never interpreted as zero.')
