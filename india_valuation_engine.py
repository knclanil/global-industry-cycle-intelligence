"""Source-aware Indian equity valuation helpers.

Inspired by the user's Factor Holdings Intelligence valuation approach.
Only reported/cached information is used; unknown != zero.
Annual operating FCF is a proxy, not certified FCFE/FCFF.
"""
from __future__ import annotations
import math
from statistics import mean
from india_financial_data import build_kpis, equity_dcf_proxy, liquidation_proxy

SCENARIOS = {
    'Bear': {'growth': 0.0, 'discount': 12.0, 'terminal': 2.0},
    'Base': {'growth': 3.0, 'discount': 11.0, 'terminal': 3.0},
    'Bull': {'growth': 5.0, 'discount': 10.0, 'terminal': 3.5},
}

def numeric(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def normalized_fcf(payload, periods=5, minimum=3, cutoff=None):
    """Mean of latest available annual historical FCF periods, including negative years.

    Requires >=3 consecutive fiscal-year observations to prevent optimistic
    cherry-picking or treating missing years as smooth cash flow.
    """
    rows = (payload.get('statements') or {}).get('annual', {}).get('cashflow', {})
    if not isinstance(rows, dict):
        return None, 0, []
    values = []
    for date, item in sorted(rows.items(), reverse=True):
        if cutoff and date > cutoff:
            continue
        if not isinstance(item, dict):
            continue
        fcf = numeric(item.get('free_cash_flow'))
        if fcf is None:
            ocf, capex = numeric(item.get('operating_cash_flow')), numeric(item.get('capital_expenditure'))
            if ocf is not None and capex is not None:
                fcf = ocf - abs(capex)
        if fcf is not None:
            values.append((date, fcf))
        if len(values) >= periods:
            break
    # Check that fiscal-year observations are approximately consecutive.
    if len(values) < minimum:
        return None, len(values), values
    from datetime import date
    try:
        dates = [date.fromisoformat(d) for d, _ in values]
        if any(not 300 <= (a-b).days <= 430 for a,b in zip(dates, dates[1:])):
            return None, len(values), values
    except ValueError:
        return None, len(values), values
    return mean(v for _, v in values), len(values), values


def scenario_table(payload, growth_overrides=None, period=None):
    """Return three DCF scenarios with margin of safety and buy-at-25%-MOS price."""
    report = build_kpis(payload, 'annual', period)
    m = report['metrics']
    fcf, years, samples = normalized_fcf(payload, cutoff=report["period"])
    shares = numeric(m.get('shares_outstanding'))
    price = numeric(m.get('price'))
    # Only compare value and price when financial and quote currencies agree.
    matching = bool(m.get('quote_currency_comparable'))
    rows = []
    for name, defaults in SCENARIOS.items():
        settings = dict(defaults)
        settings.update((growth_overrides or {}).get(name, {}))
        value = equity_dcf_proxy(fcf, shares, settings['growth'], settings['discount'], settings['terminal']) if fcf is not None and fcf > 0 else None
        mos = (100.0 * (value-price)/value) if (matching and value and price is not None and value > 0) else None
        rows.append({
            'Scenario': name, 'Growth %': settings['growth'], 'Required return %': settings['discount'],
            'Terminal growth %': settings['terminal'], 'Value / share': value,
            'Margin of safety %': mos,
            '25% MOS buy reference': value * 0.75 if value is not None else None,
        })
    return {'rows': rows, 'normalized_fcf': fcf, 'fcf_years': years,
            'fcf_samples': samples, 'shares': shares, 'price': price, 'currency_aligned': matching,
            'report': report}


def valuation_metrics(payload, period=None):
    """Pure computations from a cached annual Yahoo snapshot. Sources stay distinct."""
    report = build_kpis(payload, 'annual', period)
    m = report['metrics']
    eps, bvps = numeric(m.get('diluted_eps')), numeric(m.get('book_value_per_share'))
    price, pe = numeric(m.get('price')), numeric(m.get('pe'))
    growth = numeric(m.get('eps_yoy'))
    # Growth CAGR uses positive historical EPS, not a one-off annual jump.
    inc = ((payload.get('statements') or {}).get('annual', {}).get('income') or {})
    eps_obs = [(d, numeric(row.get('diluted_eps'))) for d,row in sorted(inc.items()) if isinstance(row, dict)]
    eps_obs = [(d,v) for d,v in eps_obs if v is not None]
    eps_cagr = None
    if len(eps_obs) >= 2:
        from datetime import date
        end_date, end = eps_obs[-1]
        earlier = [(d,v) for d,v in eps_obs[:-1]
                   if 4.5 <= (date.fromisoformat(end_date)-date.fromisoformat(d)).days / 365.25 <= 5.5]
        if earlier and end > 0 and earlier[-1][1] > 0:
            elapsed = (date.fromisoformat(end_date)-date.fromisoformat(earlier[-1][0])).days / 365.25
            eps_cagr = (pow(end / earlier[-1][1], 1 / elapsed) - 1) * 100
    info = payload.get('quote') or {}
    div_pct = numeric(info.get('dividend_yield_pct'))
    peg = pe / eps_cagr if pe is not None and eps_cagr and eps_cagr > 0 else None
    pegy = pe / (eps_cagr + div_pct) if pe is not None and eps_cagr is not None and div_pct is not None and eps_cagr + div_pct > 0 else None
    n = numeric(m.get('ncav_per_share'))
    return {'report': report, 'graham_number': math.sqrt(22.5*eps*bvps) if eps and eps > 0 and bvps and bvps > 0 else None,
            'eps_cagr_5y_pct': eps_cagr, 'peg': peg, 'pegy': pegy,
            'book_value_per_share': bvps, 'tangible_book_per_share': numeric(m.get('tangible_book_per_share')),
            'ncav_per_share': n, 'price': price, 'pe': pe, 'pb': numeric(m.get('pb')),
            'ev_to_ebitda': numeric(m.get('ev_to_ebitda')),
            'fcf_yield': numeric(m.get('fcf_yield')),
            'market_cap': numeric(m.get('market_cap')),
            'shares': numeric(m.get('shares_outstanding')),
            'liquidation_inputs': {k: m.get(k) for k in ('total_assets','cash','total_liabilities','preferred_equity','shares_outstanding')},
            'quote_currency_aligned': bool(m.get('quote_currency_comparable'))}


def earnings_valuation(normalized_eps, target_pe):
    """Illustrative price from normalized positive EPS times explicit target P/E."""
    eps, multiple = numeric(normalized_eps), numeric(target_pe)
    return eps * multiple if eps is not None and eps > 0 and multiple is not None and multiple > 0 else None


def choose_fields(nse=None, screener=None, yahoo=None):
    """Explicit precedence for quote-only fields with individual source lineage.

    Does not combine financial statement totals across providers/periods.
    """
    nse, screener, yahoo = nse or {}, screener or {}, yahoo or {}
    selected, sources = {}, {}
    for field in ('price','trailing_pe','industry_pe','forward_pe','pb','dividend_yield_pct','market_cap'):
        selected[field], sources[field] = None, 'N/A'
        for label, item in (('NSE', nse), ('Screener', screener), ('Yahoo', yahoo)):
            x = numeric(item.get(field))
            if x is not None and (x > 0 or (field == 'dividend_yield_pct' and x == 0)):
                selected[field], sources[field] = x, label
                break
    return selected, sources
