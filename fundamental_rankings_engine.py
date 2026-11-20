"""Auditable, consistency-first business fundamentals rankings.

No network access. Computes rankings from saved SEC Company Facts / India Yahoo
snapshots. Never substitutes missing values with zero. Company fundamental ranks
are independent of sector/factor market rotation and ETF membership scores.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
# Percentiles compare firms within a region and an industry cohort when sufficient.
# More than a single recent observation is mandatory; history matters.
WEIGHTS = {
    'ROE': 0.18,
    'Debt / equity': 0.13,
    'Current ratio': 0.10,
    'Operating margin': 0.15,
    'Net margin': 0.13,
    'Revenue growth': 0.12,
    'Liabilities / assets': 0.11,
    'Dividend consistency': 0.05,
    'Dividend growth': 0.03,
}
LOWER_IS_BETTER = {'Debt / equity', 'Liabilities / assets'}
MIN_YEARS = 3
MIN_METRICS = 5


def finite(v):
    try:
        v = float(v)
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _ratio(num, den, positive_den=True):
    a, b = finite(num), finite(den)
    if not np.isfinite(a) or not np.isfinite(b) or b == 0 or (positive_den and b <= 0):
        return np.nan
    return a / b


def _collect_years(rows):
    return sorted([r for r in rows if r.get('date')], key=lambda x: x['date'])


def build_history_india(payload):
    """Financial statements are stored as INR, not crore. Join period ends only."""
    annual = (payload.get('statements') or {}).get('annual') or {}
    sections = {s: (annual.get(s) or {}) for s in ('income', 'balance', 'cashflow')}
    # Financial year ends sometimes differ a few days between statement types.
    dates = sorted(set().union(*(set(v) for v in sections.values())))
    out = []
    for date in dates:
        inc = sections['income'].get(date, {})
        bal = sections['balance'].get(date, {})
        cf = sections['cashflow'].get(date, {})
        # Exclude dates with no genuine income-statement data.
        if not any(np.isfinite(finite(inc.get(k))) for k in ('revenue', 'net_income')):
            continue
        dividend = finite(cf.get('dividends_paid'))
        out.append({
            'date': date,
            'revenue': finite(inc.get('revenue')),
            'net_income': finite(inc.get('net_income')),
            'operating_income': finite(inc.get('operating_income')),
            'equity': finite(bal.get('equity')),
            'debt': finite(bal.get('total_debt')),
            'current_assets': finite(bal.get('current_assets')),
            'current_liabilities': finite(bal.get('current_liabilities')),
            'assets': finite(bal.get('total_assets')),
            'liabilities': finite(bal.get('total_liabilities')),
            'dividend': abs(dividend) if np.isfinite(dividend) else np.nan,
            'weighted_average_shares': finite(inc.get('weighted_average_shares')),
            'shares_statement': finite(bal.get('shares_statement')),
            'preferred_equity': finite(bal.get('preferred_equity')),
            'operating_cash_flow': finite(cf.get('operating_cash_flow')),
            'capital_expenditure': finite(cf.get('capital_expenditure')),
        })
    return _collect_years(out)


def build_history_sec(facts):
    """SEC XBRL annual observations. Only reported fields; missing remains NaN."""
    from fundamental_intelligence import extract_company_facts
    df = extract_company_facts(facts)
    if df.empty:
        return []
    # Extend existing SEC extraction without modifying existing page logic.
    extras = {
        'current_assets': ('AssetsCurrent',),
        'current_liabilities': ('LiabilitiesCurrent',),
        'dividend': ('PaymentsOfDividendsCommonStock', 'PaymentsOfDividends'),
    }
    extra_data = {}
    for field, tags in extras.items():
        for tag in tags:
            observations = _sec_values(facts, tag)
            if observations:
                for entry in observations:
                    extra_data.setdefault(field, {}).setdefault(entry['period_end'], entry['value'])
                break
    out = []
    for _, r in df.sort_values('period_end').iterrows():
        date = str(r['period_end'])
        if not (np.isfinite(finite(r.get('revenue'))) or np.isfinite(finite(r.get('net_income')))):
            continue
        debt = finite(r.get('debt'))
        out.append({'date': date, 'revenue': finite(r.get('revenue')),
                    'net_income': finite(r.get('net_income')),
                    'operating_income': finite(r.get('operating_income')),
                    'equity': finite(r.get('equity')), 'debt': debt,
                    'current_assets': finite(extra_data.get('current_assets', {}).get(date)),
                    'current_liabilities': finite(extra_data.get('current_liabilities', {}).get(date)),
                    'assets': finite(r.get('assets')), 'liabilities': finite(r.get('liabilities')),
                    'dividend': finite(extra_data.get('dividend', {}).get(date)),
                    'weighted_average_shares': _sec_shares(facts, date),
                    'shares_statement': finite(r.get('shares')),
                    'preferred_equity': np.nan,
                    'operating_cash_flow': finite(r.get('operating_cash_flow')),
                    'capital_expenditure': finite(r.get('capex'))})
    return _collect_years(out)


def _sec_shares(facts, period_end):
    """Get latest-filed annual weighted-average common shares for fiscal period."""
    tags = facts.get('facts', {}).get('us-gaap', {})
    for tag in ('WeightedAverageNumberOfDilutedSharesOutstanding',
                'WeightedAverageNumberOfSharesOutstandingBasic'):
        values = (tags.get(tag) or {}).get('units', {}).get('shares', [])
        candidates = []
        for x in values:
            if x.get('end') != period_end or x.get('form') not in ('10-K', '20-F', '10-K/A'):
                continue
            if x.get('start'):
                try:
                    days = (pd.Timestamp(x['end']) - pd.Timestamp(x['start'])).days
                except (ValueError, KeyError):
                    continue
                if not 330 <= days <= 380:
                    continue
            if np.isfinite(finite(x.get('val'))) and float(x['val']) > 0:
                candidates.append(x)
        if candidates:
            return float(max(candidates, key=lambda x: x.get('filed',''))['val'])
    return np.nan


def _sec_values(facts, tag):
    """Only fiscal-year facts, and only reasonably annual flow durations."""
    tags = facts.get('facts', {}).get('us-gaap', {})
    values = (tags.get(tag) or {}).get('units', {}).get('USD', [])
    records = []
    for v in values:
        if v.get('form') not in ('10-K', '20-F', '10-K/A'):
            continue
        if v.get('fp') != 'FY':
            continue
        if v.get('start'):
            try:
                duration = (pd.Timestamp(v['end']) - pd.Timestamp(v['start'])).days
            except (ValueError, KeyError):
                continue
            if not 330 <= duration <= 380:
                continue
        if not v.get('end') or not np.isfinite(finite(v.get('val'))):
            continue
        records.append({'period_end': v['end'], 'value': float(v['val']), 'filed': v.get('filed', '')})
    latest = {}
    for item in sorted(records, key=lambda d: d['filed']):
        latest[item['period_end']] = item
    return list(latest.values())


def history_metrics(history):
    """Use up to last five annual observations, and require 3 distinct years."""
    h = _collect_years(history)
    h = h[-5:]
    out = {'Years': len(h), 'As of': h[-1]['date'] if h else '', 'History': h}
    # Require sequential annual periods; three scattered old observations are not consistency.
    if len(h) >= MIN_YEARS:
        gaps = [(pd.Timestamp(h[i]['date']) - pd.Timestamp(h[i-1]['date'])).days
                for i in range(1, len(h))]
        consecutive = all(330 <= gap <= 400 for gap in gaps)
    else:
        consecutive = False
    if len(h) < MIN_YEARS or not consecutive:
        return {**out, **{k: np.nan for k in WEIGHTS}, 'Dividend observations': 0}
    series = {k: [] for k in WEIGHTS}
    revenues = []
    dividend_obs = 0
    for r in h:
        rev = finite(r.get('revenue'))
        revenues.append(rev)
        series['ROE'].append(_ratio(r.get('net_income'), r.get('equity')))
        series['Debt / equity'].append(_ratio(r.get('debt'), r.get('equity')))
        series['Current ratio'].append(_ratio(r.get('current_assets'), r.get('current_liabilities')))
        series['Operating margin'].append(_ratio(r.get('operating_income'), rev))
        series['Net margin'].append(_ratio(r.get('net_income'), rev))
        series['Liabilities / assets'].append(_ratio(r.get('liabilities'), r.get('assets')))
        series['Revenue growth'].append(np.nan)
        series['Dividend growth'].append(np.nan)
        d = finite(r.get('dividend'))
        if np.isfinite(d):
            dividend_obs += 1
            # Expense cash-flow sign already normalized, including actual zero.
            series['Dividend consistency'].append(float(d > 0))
        else:
            series['Dividend consistency'].append(np.nan)
    for i in range(1, len(h)):
        prev_div = finite(h[i-1].get('dividend'))
        cur_div = finite(h[i].get('dividend'))
        if np.isfinite(prev_div) and np.isfinite(cur_div) and prev_div > 0:
            series['Dividend growth'][i] = (cur_div / prev_div) - 1
        a, b = revenues[i], revenues[i-1]
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            series['Revenue growth'][i] = a / b - 1
    # At least 3 valid years for level metrics; 2 annual changes for growth.
    for name, vals in series.items():
        a = np.asarray(vals, dtype=float)
        good = a[np.isfinite(a)]
        min_n = 2 if name in ('Revenue growth', 'Dividend growth') else 3
        if name == 'Dividend consistency':
            # Unknown dividends are not assumed absent.
            out[name] = float(np.mean(good)) if len(good) >= 3 else np.nan
        elif len(good) >= min_n:
            # Median rewards durable outcomes, rather than one excellent year.
            out[name] = float(np.median(good))
        else:
            out[name] = np.nan
        # Stability component is directional: low dispersion is more consistent.
        out[f'{name} stability'] = (float(np.median(np.abs(good - np.median(good))))
                                           if len(good) >= 3 else np.nan)
        out[f'{name} samples'] = len(good)
    out['Dividend observations'] = dividend_obs
    return out


def _score_group(df, indexes, *, cohort_min=5):
    """Relative percentiles on observed metrics; never score a missing metric."""
    frame = df.copy()
    for name in WEIGHTS:
        x = pd.to_numeric(frame[name], errors='coerce').replace([np.inf, -np.inf], np.nan)
        if name in ('ROE', 'Debt / equity'):
            # ROE on negative equity and negative D/E ratios lack ordinary meaning.
            x = x.where(x.ge(0))
        # Winsorize for robust rank, preserving the ordering around the center.
        def score(cohort):
            valid = cohort.dropna()
            if len(valid) < cohort_min:
                return pd.Series(np.nan, index=cohort.index)
            lo, hi = valid.quantile([0.05, 0.95])
            clipped = cohort.clip(lower=lo, upper=hi)
            return clipped.rank(pct=True, ascending=name not in LOWER_IS_BETTER) * 100
        frame[f'{name} percentile'] = x.groupby(indexes, group_keys=False).transform(score)
    return frame


def rank_fundamentals(df, min_years=MIN_YEARS, min_metrics=MIN_METRICS):
    """Sector-relative quality ranking with strict coverage and consistency rules.

    The ranking uses original financials only, never sector momentum, ETF weight,
    market price, or proxies for missing financial data.
    """
    if df.empty:
        return df.copy()
    out = df.copy()
    out['Sector'] = out.get('Sector', pd.Series('Unclassified', index=out.index)).fillna('Unclassified').astype(str)
    out['Region'] = out.get('Region', pd.Series('Unknown', index=out.index)).fillna('Unknown').astype(str)
    out = _score_group(out, [out['Region'], out['Sector']])
    vals = [f'{k} percentile' for k in WEIGHTS]
    arr = out[vals].to_numpy(dtype=float)
    weights = np.asarray(list(WEIGHTS.values()), dtype=float)
    good = np.isfinite(arr)
    weighted_sum = np.where(good, arr * weights, 0).sum(axis=1)
    covered_w = (good * weights).sum(axis=1)
    out['Metrics covered'] = good.sum(axis=1)
    out['Metric coverage %'] = np.round(covered_w * 100, 1)
    # Stability: year-to-year ROE, operating/net-margin volatility. Scaled to
    # each company's long-term metric level; do NOT invent missing history.
    stability = []
    for _, r in out.iterrows():
        avail = []
        for k in ('ROE', 'Operating margin', 'Net margin'):
            level, mad = finite(r.get(k)), finite(r.get(f'{k} stability'))
            if np.isfinite(level) and np.isfinite(mad):
                scale = max(abs(level), 0.05)
                avail.append(max(0, 100 * (1 - min(mad / scale, 1))))
        stability.append(np.mean(avail) if len(avail) >= 2 else np.nan)
    out['Consistency'] = stability
    base = np.divide(weighted_sum, covered_w, out=np.full(len(out), np.nan), where=covered_w > 0)
    # Missing financials are never zero. Insufficient coverage is unranked.
    eligible = (out['Years'] >= min_years) & (out['Metrics covered'] >= min_metrics) & (out['Metric coverage %'] >= 60) & out['Consistency'].notna()
    out['Fundamental score'] = np.where(eligible, np.round(0.85 * base + 0.15 * out['Consistency'], 1), np.nan)
    out['Status'] = np.where(eligible, 'Ranked', 'Insufficient verified financial history / peer coverage')
    out['Rank'] = np.nan
    for region, idx in out.loc[eligible].groupby('Region').groups.items():
        ordered = out.loc[idx, 'Fundamental score'].rank(method='min', ascending=False)
        out.loc[idx, 'Rank'] = ordered
    return out.sort_values(['Region', 'Fundamental score', 'Ticker'], ascending=[True, False, True], na_position='last')


def load_india_profiles():
    """Company-by-company saved annual Yahoo financials; no bulk live requests."""
    folder = DATA / 'india_financials' / 'companies'
    rows = []
    for p in folder.glob('*.json'):
        try:
            payload = json.loads(p.read_text(encoding='utf-8'))
            h = build_history_india(payload)
            vals = history_metrics(h)
            from fundamental_valuation_engine import evaluate
            valuation = evaluate(h, sector=payload.get('industry') or payload.get('sector') or '')
            rows.append({'Region': 'India', 'Ticker': payload.get('symbol', ''),
                         'Company': payload.get('company_name', ''),
                         'Sector': payload.get('industry') or payload.get('sector') or 'Unclassified',
                         'Source': 'Yahoo snapshot', **vals, **valuation})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return pd.DataFrame(rows)


def load_sec_profiles(region):
    """Only match SEC cached filings to independently verified ETF companies."""
    from fundamental_intelligence import load_universe, _cached_cik_index, _resolve_cached, _is_us, STORE
    universe = load_universe()
    if universe.empty:
        return pd.DataFrame()
    universe = universe[universe.region.eq(region)].drop_duplicates('issuer_id')
    directory_path = STORE / 'sec_company_directory.json'
    try:
        directory = pd.DataFrame(json.loads(directory_path.read_text())) if directory_path.exists() else pd.DataFrame()
    except (ValueError, OSError):
        directory = pd.DataFrame()
    index = _cached_cik_index()
    out = []
    seen = set()
    for r in universe.itertuples(index=False):
        if not _is_us(r.country):
            continue
        cik = _resolve_cached(r.ticker, r.company, directory, index)
        if cik is None or cik in seen:
            continue
        path = STORE / f'facts_{cik:010d}.json'
        if not path.exists():
            continue
        seen.add(cik)
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            h = build_history_sec(payload)
            vals = history_metrics(h)
            from fundamental_valuation_engine import evaluate
            valuation = evaluate(h, sector=r.sector)
            out.append({'Region': region, 'Ticker': r.ticker, 'Company': r.company,
                        'Sector': r.sector, 'Source': 'SEC EDGAR', 'CIK': cik, **vals, **valuation})
        except (ValueError, OSError, KeyError, TypeError):
            continue
    return pd.DataFrame(out)


def get_rankings(region):
    if region not in ('USA', 'Global', 'India'):
        raise ValueError('Invalid region')
    profiles = load_india_profiles() if region == 'India' else load_sec_profiles(region)
    return rank_fundamentals(profiles) if not profiles.empty else profiles
