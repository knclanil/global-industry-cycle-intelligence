"""Verified NSE India index rotation extension for the Knowledge Graph builder.

No fabricated price data or inferred rotation. The synthetic source IDs below are
internal identifiers, NOT Yahoo Finance ticker symbols.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

import numpy as np
import pandas as pd

@dataclass(frozen=True)
class IndexSpec:
    slug: str
    nse_name: str
    kind: str
    label: str

# NSE names follow the official index-title vocabulary in india_constituents.py.
EXTRA_INDIA_INDICES = (
    IndexSpec('nifty_oil_gas', 'NIFTY OIL & GAS', 'sector', 'Nifty Oil & Gas'),
    IndexSpec('nifty_india_defence', 'NIFTY INDIA DEFENCE', 'sector', 'Nifty India Defence'),
    IndexSpec('nifty_india_manufacturing', 'NIFTY INDIA MANUFACTURING', 'sector', 'Nifty India Manufacturing'),
    IndexSpec('nifty500_low_volatility_50', 'NIFTY500 LOW VOLATILITY 50', 'factor', 'Low Volatility'),
    IndexSpec('nifty500_momentum_50', 'NIFTY500 MOMENTUM 50', 'factor', 'Momentum'),
    IndexSpec('nifty500_quality_50', 'NIFTY500 QUALITY 50', 'factor', 'Quality'),
    IndexSpec('nifty500_value_50', 'NIFTY500 VALUE 50', 'factor', 'Value'),
    IndexSpec('nifty200_value_30', 'NIFTY200 VALUE 30', 'factor', 'Value'),
    IndexSpec('nifty200_alpha_30', 'NIFTY200 ALPHA 30', 'factor', 'Alpha'),
    IndexSpec('nifty_low_volatility_50', 'NIFTY LOW VOLATILITY 50', 'factor', 'Low Volatility'),
    IndexSpec('nifty_dividend_opportunities_50', 'NIFTY DIVIDEND OPPORTUNITIES 50', 'factor', 'Dividend'),
    IndexSpec('nifty100_quality_30', 'NIFTY100 QUALITY 30', 'factor', 'Quality'),
    IndexSpec('nifty500_growth_50', 'NIFTY500 GROWTH 50', 'factor', 'Growth'),
)

SOURCE_TICKERS = {s.slug: f'NSE_INDEX:{s.slug}' for s in EXTRA_INDIA_INDICES}


def _normalized_close(frame: pd.DataFrame) -> pd.Series:
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    name = 'Adj Close' if 'Adj Close' in frame else 'Close' if 'Close' in frame else None
    if name is None:
        return pd.Series(dtype=float)
    series = pd.to_numeric(frame[name], errors='coerce')
    dt = pd.to_datetime(series.index, errors='coerce', utc=True)
    series.index = dt.tz_convert(None).normalize()
    series = series.loc[series.index.notna() & series.gt(0)].sort_index()
    # Reject duplicate timestamps with conflicting values rather than silently inventing a price.
    if series.index.has_duplicates:
        for _, grp in series.groupby(level=0):
            if grp.nunique() > 1:
                return pd.Series(dtype=float)
        series = series.loc[~series.index.duplicated(keep='last')]
    return series


def calculate_signal(index_close: pd.Series, benchmark_close: pd.Series, lookback: int, *,
                     benchmark_max_age_days: int = 7) -> tuple[dict | None, str]:
    """Use repository's relative-strength / lagged-momentum formula.

    Require L + floor(L/2) + 1 aligned observations, positive closes, and recent overlap.
    """
    p = pd.concat([index_close.rename('index'), benchmark_close.rename('benchmark')], axis=1).dropna()
    p = p.loc[p['index'].gt(0) & p['benchmark'].gt(0)].sort_index()
    required = lookback + lookback // 2 + 1
    if len(p) < required:
        return None, f'Insufficient aligned sessions ({len(p)}/{required})'
    if (benchmark_close.index.max() - p.index.max()).days > benchmark_max_age_days:
        return None, 'Index/benchmark history is stale or nonoverlapping'
    relative = p['index'] / p['benchmark']
    rs = 100.0 * (relative.iloc[-1] / relative.iloc[-1 - lookback] - 1.0)
    older_rs = 100.0 * (relative.iloc[-1 - lookback // 2] /
                        relative.iloc[-1 - lookback // 2 - lookback] - 1.0)
    momentum = rs - older_rs
    if not np.isfinite(rs) or not np.isfinite(momentum):
        return None, 'Non-finite rotation statistics'
    quadrant = ('Leading' if momentum >= 0 else 'Weakening') if rs >= 0 else ('Improving' if momentum >= 0 else 'Lagging')
    return {'relative_strength': round(float(rs), 3), 'rs_momentum': round(float(momentum), 3),
            'quadrant': quadrant, 'as_of': str(p.index.max().date())}, ''


def fetch_nse_index_history(nse_name: str, *, start: date, end: date) -> pd.DataFrame:
    """Fetch a real price series; if both NSE readers fail, report the failure."""
    problems = []
    try:
        import nsepython_provider
        data = nsepython_provider.history(nse_name, start, end)
        if not data.empty:
            return data
        problems.append('nsepython returned empty history')
    except Exception as exc:
        problems.append(f'nsepython: {type(exc).__name__}: {exc}')
    try:
        import requests
        import india_market_data as india
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0',
                                'Accept': 'application/json, text/plain, */*',
                                'Referer': 'https://www.nseindia.com/'})
        data = india._nse_history(session, nse_name, start, end)
        if not data.empty:
            return data
        problems.append('NSE API returned empty history')
    except Exception as exc:
        problems.append(f'NSE API: {type(exc).__name__}: {exc}')
    raise RuntimeError('; '.join(problems))


def build_extra_signals(benchmark_frame: pd.DataFrame, lookbacks=(21, 63, 126),
                        fetcher: Callable | None = None) -> tuple[dict[int, pd.DataFrame], pd.DataFrame]:
    """Fetch once per index, evaluate three lookbacks, collect honest diagnostics."""
    if fetcher is None:
        fetcher = fetch_nse_index_history
    benchmark = _normalized_close(benchmark_frame)
    signals = {int(L): [] for L in lookbacks}
    diagnostics = []
    if benchmark.empty:
        for spec in EXTRA_INDIA_INDICES:
            for L in lookbacks:
                diagnostics.append({'index_slug': spec.slug, 'index_name': spec.nse_name,
                                    'lookback_sessions': int(L), 'status': 'unavailable',
                                    'reason': 'Nifty 50 benchmark price history unavailable'})
        return {L: pd.DataFrame() for L in signals}, pd.DataFrame(diagnostics)
    end = benchmark.index.max().date()
    start = end - timedelta(days=max(450, int(max(lookbacks)) * 4))
    for spec in EXTRA_INDIA_INDICES:
        try:
            history = fetcher(spec.nse_name, start=start, end=end)
            source_close = _normalized_close(history)
            if source_close.empty:
                raise ValueError('No valid close series')
            for L in lookbacks:
                result, error = calculate_signal(source_close, benchmark, int(L))
                if result is None:
                    diagnostics.append({'index_slug': spec.slug, 'index_name': spec.nse_name,
                                        'lookback_sessions': int(L), 'status': 'unavailable', 'reason': error})
                    continue
                signals[int(L)].append({'region': 'India', 'kind': spec.kind,
                    'source_id': SOURCE_TICKERS[spec.slug], 'label': spec.label,
                    'index_name': spec.nse_name, **result, 'source': 'NSE index historical close'})
                diagnostics.append({'index_slug': spec.slug, 'index_name': spec.nse_name,
                                    'lookback_sessions': int(L), 'status': 'verified', 'reason': ''})
        except Exception as exc:
            for L in lookbacks:
                diagnostics.append({'index_slug': spec.slug, 'index_name': spec.nse_name,
                                    'lookback_sessions': int(L), 'status': 'unavailable',
                                    'reason': f'{type(exc).__name__}: {exc}'})
    return {L: pd.DataFrame(rows) for L, rows in signals.items()}, pd.DataFrame(diagnostics)
