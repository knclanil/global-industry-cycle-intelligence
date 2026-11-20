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
LEGACY_WEIGHTS = {
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
# Quality Model V3: separate durable business economics from stock valuation.
# Domain weights sum to 100%; financial institutions have a different domain model.
DIMENSION_WEIGHTS = {
    'Profitability & capital efficiency': .25,
    'Financial strength': .20,
    'Growth quality': .20,
    'Cash flow quality': .20,
    'Historical consistency': .15,
}
FINANCIAL_DIMENSION_WEIGHTS = {
    'Profitability & capital efficiency': .35,
    'Financial strength': .25,
    'Growth quality': .25,
    'Historical consistency': .15,
}
# Retain original KPI indicators for the existing comparison table and exports.
WEIGHTS = LEGACY_WEIGHTS

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
    # Five-year cash-generation and shareholder-value diagnostics.
    fcf_series = []
    conversion = []
    diluted_eps_series = []
    positive_earnings = []
    positive_fcf = []
    for row in h:
        cfo, capex = finite(row.get('operating_cash_flow')), finite(row.get('capital_expenditure'))
        fcf = cfo - abs(capex) if np.isfinite(cfo) and np.isfinite(capex) else np.nan
        fcf_series.append(fcf)
        ni = finite(row.get('net_income'))
        positive_earnings.append(float(ni > 0) if np.isfinite(ni) else np.nan)
        positive_fcf.append(float(fcf > 0) if np.isfinite(fcf) else np.nan)
        conversion.append(_ratio(cfo, ni) if np.isfinite(ni) and ni > 0 else np.nan)
        shares = finite(row.get('weighted_average_shares'))
        if not np.isfinite(shares) or shares <= 0:
            shares = finite(row.get('shares_statement'))
        diluted_eps_series.append(_ratio(ni, shares))
    def _median_valid(vals, count=3):
        valid = np.asarray(vals, dtype=float)
        valid = valid[np.isfinite(valid)]
        return float(np.median(valid)) if len(valid) >= count else np.nan
    out['FCF margin'] = _median_valid([_ratio(fcf, revenue) for fcf, revenue in zip(fcf_series, revenues)])
    out['Cash conversion'] = _median_valid(conversion)
    out['Positive FCF years'] = _median_valid(positive_fcf)
    out['Positive earnings years'] = _median_valid(positive_earnings)
    out['FCF observations'] = sum(np.isfinite(v) for v in fcf_series)
    out['Revenue CAGR'] = (revenues[-1] / revenues[0]) ** (1 / (len(h) - 1)) - 1 if (len(h) >= 3 and np.isfinite(revenues[0]) and revenues[0] > 0 and np.isfinite(revenues[-1]) and revenues[-1] > 0) else np.nan
    good_eps = [v for v in diluted_eps_series if np.isfinite(v)]
    out['EPS CAGR'] = (good_eps[-1] / good_eps[0]) ** (1 / (len(good_eps)-1)) - 1 if (len(good_eps) >= 3 and good_eps[0] > 0 and good_eps[-1] > 0 and len(good_eps) == len(h)) else np.nan
    out['FCF CAGR'] = (fcf_series[-1] / fcf_series[0]) ** (1 / (len(h)-1)) - 1 if (len(h) >= 3 and np.isfinite(fcf_series[0]) and fcf_series[0] > 0 and np.isfinite(fcf_series[-1]) and fcf_series[-1] > 0 and all(np.isfinite(v) for v in fcf_series)) else np.nan
    # ROIC requires taxes and invested capital; not reconstructed from ambiguous tags.
    out['ROIC'] = np.nan
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


def _is_financial_sector(sector):
    value = str(sector).lower()
    return any(x in value for x in ('bank', 'insurance', 'financial services', 'nbfc', 'lending', 'credit institution'))


def _metric_percentile(frame, name, direction, cohort_min=5):
    x = pd.to_numeric(frame.get(name, pd.Series(np.nan, index=frame.index)), errors='coerce').replace([np.inf, -np.inf], np.nan)
    if name in ('ROE', 'Debt / equity'):
        x = x.where(x.ge(0))
    def compare(group):
        valid = group.dropna()
        if len(valid) < cohort_min:
            return pd.Series(np.nan, index=group.index)
        low, high = valid.quantile([.05, .95])
        return group.clip(low, high).rank(pct=True, ascending=(direction == 'higher')) * 100
    return x.groupby([frame['Region'], frame['Sector']], group_keys=False).transform(compare)


def _consistency_from_history(row):
    h = row.get('History')
    if not isinstance(h, list) or len(h) < 3:
        return np.nan
    good_years = [r for r in h if np.isfinite(finite(r.get('net_income')))]
    if len(good_years) < 3:
        return np.nan
    ratios = []
    for name in ('ROE', 'Operating margin', 'Net margin', 'Revenue growth'):
        level, mad = finite(row.get(name)), finite(row.get(f'{name} stability'))
        if np.isfinite(level) and np.isfinite(mad):
            ratios.append(max(0, 100 * (1 - min(mad / max(abs(level), .05), 1))))
    stability = float(np.median(ratios)) if len(ratios) >= 2 else np.nan
    positives = [float(r['net_income'] > 0) for r in good_years]
    persistence = 100 * sum(positives)/len(positives)
    if not np.isfinite(stability):
        return np.nan
    # Stable profitability, recurring earnings and observed cash-flow persistence.
    return .55 * stability + .30 * persistence + .15 * (100 * finite(row.get('Positive FCF years')) if np.isfinite(finite(row.get('Positive FCF years'))) else persistence)


def rank_fundamentals(df, min_years=MIN_YEARS, min_metrics=MIN_METRICS):
    """Multi-year quality model V3. Peers grouped by region and industry.

    Eligibility: 3 consecutive fiscal years, at least 3 supported quality
    dimensions (including financial strength), >=70% eligible domain weight,
    and at least 5 observed annual KPIs. Missing data never gets a zero score.
    Point-in-time reference snapshots are categorically ineligible.
    """
    if df.empty:
        return df.copy()
    out = df.copy()
    out['Sector'] = out.get('Sector', pd.Series('Unclassified', index=out.index)).fillna('Unclassified').astype(str)
    out['Region'] = out.get('Region', pd.Series('Unknown', index=out.index)).fillna('Unknown').astype(str)
    for key in ('ROE','Operating margin','Net margin','Debt / equity','Current ratio',
                'Liabilities / assets','Revenue CAGR','EPS CAGR','FCF CAGR',
                'FCF margin','Cash conversion','Positive FCF years','Dividend consistency',
                'Dividend growth', 'Positive earnings years'):
        if key not in out:
            out[key] = np.nan
    definitions = {
        'ROE': 'higher', 'Operating margin': 'higher', 'Net margin': 'higher',
        'Debt / equity': 'lower', 'Current ratio': 'higher',
        'Liabilities / assets': 'lower', 'Revenue CAGR': 'higher',
        'EPS CAGR': 'higher', 'FCF CAGR': 'higher', 'FCF margin': 'higher',
        'Cash conversion': 'higher', 'Positive FCF years': 'higher',
        'Dividend consistency': 'higher', 'Dividend growth': 'higher',
        'Positive earnings years': 'higher',
    }
    for field, direction in definitions.items():
        out[field + ' percentile'] = _metric_percentile(out, field, direction)
    out['Financial institution'] = out['Sector'].map(_is_financial_sector)
    out['Historical consistency'] = out.apply(_consistency_from_history, axis=1)
    scores = []
    coverage = []
    covered_metrics = []
    statuses = []
    for _, row in out.iterrows():
        financial = bool(row['Financial institution'])
        dimensions = {
            'Profitability & capital efficiency': ['ROE','Operating margin','Net margin'],
            'Financial strength': ['Liabilities / assets','Debt / equity','Current ratio'],
            'Growth quality': ['Revenue CAGR','EPS CAGR'],
            'Cash flow quality': ['FCF margin','Cash conversion','Positive FCF years','FCF CAGR','Dividend consistency','Dividend growth'],
        }
        if financial:
            # Industrial working-capital and debt metrics distort banks.
            dimensions['Financial strength'] = ['Liabilities / assets']
            dimensions['Profitability & capital efficiency'] = ['ROE','Net margin']
            dimensions['Growth quality'] = ['Revenue CAGR','EPS CAGR']
            dimensions.pop('Cash flow quality')
        weights = FINANCIAL_DIMENSION_WEIGHTS if financial else DIMENSION_WEIGHTS
        domain_scores = {}
        observed = set()
        for domain, metrics in dimensions.items():
            points = [finite(row.get(m + ' percentile')) for m in metrics]
            valid = [point for point in points if np.isfinite(point)]
            for m, p in zip(metrics, points):
                if np.isfinite(p): observed.add(m)
            # At least half of each domain's inputs, rounded up.
            if len(valid) >= (len(metrics)+1)//2:
                domain_scores[domain] = float(np.mean(valid))
        historical = finite(row.get('Historical consistency'))
        if np.isfinite(historical):
            domain_scores['Historical consistency'] = historical
        weight_covered = sum(weights[k] for k in domain_scores)
        covered_dims = len(domain_scores)
        coverage.append(round(100 * weight_covered, 1))
        covered_metrics.append(len(observed))
        valid_history = (finite(row.get('Years')) >= min_years and
                         isinstance(row.get('History'), list) and len(row.get('History')) >= min_years)
        eligible = (valid_history and covered_dims >= 3 and
                    'Financial strength' in domain_scores and
                    'Historical consistency' in domain_scores and
                    weight_covered >= .70 and len(observed) >= min_metrics)
        # Avoid inflating weaker-coverage companies to full scores.
        score = sum(weights[k] * domain_scores[k] for k in domain_scores) if eligible else np.nan
        scores.append(round(score, 1) if np.isfinite(score) else np.nan)
        statuses.append('Ranked' if eligible else 'Insufficient multiyear history / industry-peer coverage')
        for domain in weights:
            out.loc[row.name, domain + ' score'] = domain_scores.get(domain, np.nan)
    out['Metrics covered'] = covered_metrics
    out['Metric coverage %'] = coverage
    out['Consistency'] = out['Historical consistency']
    out['Fundamental score'] = scores
    out['Status'] = statuses
    out['Rank'] = np.nan
    for region, idx in out.loc[out.Status.eq('Ranked')].groupby('Region').groups.items():
        out.loc[idx, 'Rank'] = out.loc[idx, 'Fundamental score'].rank(method='min', ascending=False)
    return out.sort_values(['Region','Fundamental score','Ticker'],ascending=[True,False,True],na_position='last')


def load_india_reference_snapshot():
    """Read historical *point-in-time* ratio snapshots from the supplied reference project.

    This is a snapshot of published/provider ratios, NOT annual financial history.
    It must never be promoted to a five-year quality/consistency ranking or
    used to calculate the user's statement-derived Graham EPS or DCF.
    """
    # Streamlit deployments can run with the project root or nightly_build as cwd.
    # Prefer the module-local file, then explicit conventional app directories.
    candidates = [
        DATA / 'india_financials' / 'reference_snapshot.csv',
        ROOT / 'nightly_build' / 'data' / 'india_financials' / 'reference_snapshot.csv',
        Path.cwd() / 'data' / 'india_financials' / 'reference_snapshot.csv',
        Path.cwd() / 'nightly_build' / 'data' / 'india_financials' / 'reference_snapshot.csv',
    ]
    source = next((candidate for candidate in candidates if candidate.is_file()), None)
    if source is None:
        return pd.DataFrame()
    try:
        raw = pd.read_csv(source, dtype={'symbol': str})
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame()
    if 'symbol' not in raw.columns:
        return pd.DataFrame()
    # Optional verified NSE holdings directory: never infer membership.
    companies = DATA / 'india_holdings' / 'company_directory.csv'
    sectors = {}
    names = {}
    if companies.exists():
        try:
            directory = pd.read_csv(companies, dtype=str).fillna('')
            for _, record in directory.iterrows():
                key = str(record.get('symbol', '')).strip().upper()
                if key:
                    sectors[key] = record.get('industry', '') or 'Unclassified'
                    names[key] = record.get('company_name', '') or key
        except (OSError, ValueError, pd.errors.ParserError):
            pass
    mapping = {
        'ROE': 'roe_pct', 'Debt / equity': 'debt_equity_ratio',
        'Current ratio': 'current_ratio',
        'Operating margin': 'operating_margin_pct', 'Net margin': 'profit_margin_pct',
        'Revenue growth': 'revenue_growth_pct',
        'Liabilities / assets': 'liabilities_assets_pct',
    }
    rows = []
    for _, record in raw.iterrows():
        ticker = str(record.get('symbol', '')).strip().upper().removesuffix('.NS')
        if not ticker or ticker.lower() == 'nan':
            continue
        metrics = {key: np.nan for key in WEIGHTS}
        for metric, column in mapping.items():
            val = finite(record.get(column))
            if np.isfinite(val):
                metrics[metric] = val / 100 if metric in (
                    'ROE', 'Operating margin', 'Net margin',
                    'Revenue growth', 'Liabilities / assets') else val
        # A provider's single snapshot does not provide 3 distinct annual observations.
        rows.append({
            'Region': 'India', 'Ticker': ticker, 'Company': names.get(ticker, ticker),
            'Sector': sectors.get(ticker, 'Unclassified'),
            'Source': 'Reference NSE/Yahoo snapshot (single period)',
            'As of': str(record.get('last_success_utc', '') or ''),
            'Years': 0, 'History': [], 'Dividend observations': 0,
            'Financial data type': 'Single-period ratio snapshot',
            'Revenue INR': finite(record.get('revenue_inr')),
            'Market cap INR': finite(record.get('market_cap_inr')),
            'P/E': finite(record.get('pe_ttm')),
            'P/B': finite(record.get('pb')),
            'Dividend yield %': finite(record.get('dividend_yield_pct')),
            **metrics,
        })
    return pd.DataFrame(rows).drop_duplicates('Ticker', keep='last')


def load_india_profiles():
    """Merge verified multi-year Yahoo financials with reference snapshot coverage.

    Multi-year statement histories win over point-in-time data, and a snapshot
    is never used to fill missing years or artificially qualify a rank.
    """
    folder = DATA / 'india_financials' / 'companies'
    rows = []
    for p in sorted(folder.glob('*.json')):
        try:
            payload = json.loads(p.read_text(encoding='utf-8'))
            h = build_history_india(payload)
            vals = history_metrics(h)
            from fundamental_valuation_engine import evaluate
            valuation = evaluate(h, sector=payload.get('industry') or payload.get('sector') or '')
            ticker = str(payload.get('symbol', '')).strip().upper().removesuffix('.NS')
            if not ticker:
                continue
            rows.append({'Region': 'India', 'Ticker': ticker,
                         'Company': payload.get('company_name') or ticker,
                         'Sector': payload.get('industry') or payload.get('sector') or 'Unclassified',
                         'Source': 'Yahoo annual statement snapshot',
                         'Financial data type': 'Annual financial statements',
                         **vals, **valuation})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    annual = pd.DataFrame(rows)
    reference = load_india_reference_snapshot()
    if annual.empty:
        return reference
    if reference.empty:
        return annual
    existing = set(annual.Ticker)
    return pd.concat([annual, reference[~reference.Ticker.isin(existing)]],
                     ignore_index=True, sort=False)

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


def snapshot_comparison(india_profiles: pd.DataFrame) -> pd.DataFrame:
    """Single-date Indian ratio comparison; deliberately NOT historical quality ranks.

    Only observed, comparable ratios are used. This offers a useful nonblank
    research screen while preserving the three-year requirement for quality rank.
    """
    if india_profiles.empty:
        return india_profiles.copy()
    frame = india_profiles.copy()
    supported = [name for name in WEIGHTS if name not in
                 ('Dividend consistency', 'Dividend growth')]
    for name in supported:
        if name not in frame.columns:
            frame[name] = np.nan
        data = pd.to_numeric(frame[name], errors='coerce').replace([np.inf, -np.inf], np.nan)
        if name in ('ROE', 'Debt / equity'):
            data = data.where(data.ge(0))
        valid = data.dropna()
        if len(valid) < 5:
            frame[name + ' snapshot percentile'] = np.nan
            continue
        lo, hi = valid.quantile([0.05, 0.95])
        frame[name + ' snapshot percentile'] = data.clip(lo, hi).rank(
            pct=True, ascending=name not in LOWER_IS_BETTER) * 100
    weights = np.array([WEIGHTS[name] for name in supported], dtype=float)
    scores = frame[[name + ' snapshot percentile' for name in supported]].to_numpy(dtype=float)
    available = np.isfinite(scores)
    coverage = (available * weights).sum(axis=1) / weights.sum()
    numerator = (np.where(available, scores, 0) * weights).sum(axis=1)
    denominator = (available * weights).sum(axis=1)
    frame['Snapshot metric coverage %'] = np.round(100 * coverage, 1)
    # At least four ratios and 60% of available indicator weights; not a
    # substitute for multi-year financial history or industry-relative scoring.
    eligible = (available.sum(axis=1) >= 4) & (coverage >= .60)
    score = np.divide(numerator, denominator,
                      out=np.full(len(frame), np.nan), where=denominator > 0)
    frame['Snapshot comparison / 100'] = np.where(eligible, np.round(score, 1), np.nan)
    frame['Snapshot position'] = frame['Snapshot comparison / 100'].rank(
        method='min', ascending=False)
    return frame.sort_values(['Snapshot comparison / 100', 'Ticker'],
                             ascending=[False, True], na_position='last')
