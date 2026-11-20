"""Transparent valuations derived from saved company financial statements only.

No web-reported EPS, market-price EPS or published intrinsic-value estimates.
The Graham Number uses derived earnings per share (net income / verified share
count). A cash-flow figure cannot be EPS: EPS is an earnings measure.

The illustrative DCF discounts cash flow from operations minus capital
expenditures. This is NOT rigorously reconstructed FCFE (net borrowing is not
known) and is deliberately labeled a simplified FCF proxy. No single fair
value is asserted. No debt is double-counted in this proxy model.
"""
from __future__ import annotations
import math
import numpy as np

SCENARIOS = {
    'Bear': (0.00, 0.12, 0.02),
    'Base': (0.03, 0.11, 0.03),
    'Bull': (0.05, 0.10, 0.035),
}


def num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else math.nan
    except (ValueError, TypeError):
        return math.nan


def derived_eps(net_income, shares):
    """Return accounting earnings per share, NOT cash flow per share."""
    profit, count = num(net_income), num(shares)
    return profit / count if math.isfinite(profit) and math.isfinite(count) and count > 0 else math.nan


def graham_number(eps, book_value_per_share):
    """Graham Number only defined for positive EPS and positive common BVPS."""
    e, b = num(eps), num(book_value_per_share)
    return math.sqrt(22.5 * e * b) if math.isfinite(e) and math.isfinite(b) and e > 0 and b > 0 else math.nan


def annual_fcf(row):
    cfo, capex = num(row.get('operating_cash_flow')), num(row.get('capital_expenditure'))
    if not (math.isfinite(cfo) and math.isfinite(capex)):
        return math.nan
    return cfo - abs(capex)


def dcf_fcf_proxy(fcf, shares, growth, discount, terminal, horizon=5):
    """Illustrative per-share discounted FCF proxy, not enterprise/FCFE DCF."""
    f, s = num(fcf), num(shares)
    if not (math.isfinite(f) and f > 0 and math.isfinite(s) and s > 0
            and -0.9 < growth < 1 and 0 < discount < 1 and 0 <= terminal < discount):
        return math.nan
    flows = [f * (1 + growth) ** year for year in range(1, horizon + 1)]
    pv = sum(amount / (1 + discount) ** year for year, amount in enumerate(flows, 1))
    perpetuity = flows[-1] * (1 + terminal) / (discount - terminal)
    return (pv + perpetuity / (1 + discount) ** horizon) / s


def evaluate(history, *, sector=''):
    """Compute valuation from SAME-PERIOD reported net income, equity, shares.

    Annual FCF must come from at least three consecutive fiscal years, all
    positive. A share count is mandatory; if based on period-end shares rather
    than weighted averages, output explicitly identifies this approximation.
    """
    history = sorted((r for r in history if r.get('date')), key=lambda r: r['date'])
    result = {'Calculated EPS': math.nan, 'FCF / share': math.nan, 'Book value / share': math.nan,
              'Graham number': math.nan, 'DCF Bear': math.nan,
              'DCF Base': math.nan, 'DCF Bull': math.nan,
              'FCF observations': 0, 'EPS share basis': 'Not available',
              'Valuation note': '', 'Valuation as of': history[-1]['date'] if history else ''}
    if not history:
        result['Valuation note'] = 'No annual financial statements'
        return result
    last = history[-1]
    shares = num(last.get('weighted_average_shares'))
    basis = 'Reported weighted-average common shares'
    if not math.isfinite(shares) or shares <= 0:
        shares = num(last.get('shares_statement'))
        basis = 'Reported period-end ordinary shares (EPS approximation)'
    result['EPS share basis'] = basis if math.isfinite(shares) and shares > 0 else 'No reported share count'
    eps = derived_eps(last.get('net_income'), shares)
    # Equity must be attributable to common equity holders; if preferred
    # shares exist and preferred claim is not reported, don't infer it.
    common_equity = num(last.get('equity'))
    preferred = num(last.get('preferred_equity'))
    if math.isfinite(common_equity) and math.isfinite(preferred):
        common_equity -= preferred
    book = common_equity / shares if (math.isfinite(common_equity) and math.isfinite(shares) and shares > 0) else math.nan
    latest_fcf = annual_fcf(last)
    fcf_per_share = (latest_fcf / shares if math.isfinite(latest_fcf) and math.isfinite(shares) and shares > 0 else math.nan)
    result.update({'Calculated EPS': eps, 'FCF / share': fcf_per_share, 'Book value / share': book,
                   'Graham number': graham_number(eps, book)})

    # Avoid a generic industrial FCF model for deposit-taking institutions.
    financial = any(k in str(sector).lower() for k in ('bank', 'insurance', 'financial services', 'nbfc', 'lending'))
    if financial:
        result['Valuation note'] = 'FCF DCF omitted: financial businesses require a different valuation framework'
        return result
    recent = history[-5:]
    fcf_values = [annual_fcf(r) for r in recent]
    result['FCF observations'] = sum(math.isfinite(v) for v in fcf_values)
    if (len(recent) < 3 or any(not math.isfinite(v) for v in fcf_values[-3:])
            or any(v <= 0 for v in fcf_values[-3:])):
        result['Valuation note'] = 'DCF requires three recent annual periods with positive, verified CFO and capex'
        return result
    # Require adjacent annual fiscal periods; snapshots cannot be spliced.
    try:
        import pandas as pd
        gaps = [(pd.Timestamp(recent[i]['date']) - pd.Timestamp(recent[i-1]['date'])).days
                for i in range(len(recent)-2, len(recent))]
        if any(g < 330 or g > 400 for g in gaps):
            result['Valuation note'] = 'DCF unavailable: recent cash-flow periods are not consecutive years'
            return result
    except (ValueError, TypeError, IndexError):
        result['Valuation note'] = 'DCF unavailable: invalid reporting dates'
        return result
    # Normalization across up to five verified positive annual FCF observations.
    used = [v for v in fcf_values if math.isfinite(v) and v > 0]
    if len(used) < 3 or not (math.isfinite(shares) and shares > 0):
        result['Valuation note'] = 'DCF unavailable: insufficient FCF or verified share count'
        return result
    normalized = float(np.median(used))
    for name, (g, r, t) in SCENARIOS.items():
        result[f'DCF {name}'] = dcf_fcf_proxy(normalized, shares, g, r, t)
    result['Valuation note'] = 'DCF is illustrative: discounts CFO − capex; not independently verified FCFE'
    return result
