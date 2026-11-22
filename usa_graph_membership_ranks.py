"""Read-only USA ranking enrichment for Knowledge Graph membership summary.

Rankings are calculated over the USA verified universe upstream, never over the
subset selected in a graph. Existing graph layout, filters, and membership rows
are not changed here. No network requests are performed in Streamlit.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RANKINGS = ROOT / 'data' / 'usa_research' / 'fundamental_rankings.csv'
METRICS = ('roe', 'current_ratio', 'operating_margin', 'net_margin', 'eps_growth_pct')
DISPLAY = {
    'roe': 'ROE %', 'current_ratio': 'Current Ratio',
    'operating_margin': 'Operating Margin %', 'net_margin': 'Net Margin %',
    'eps_growth_pct': 'EPS Growth %',
}


def _ticker(value):
    if value is None or pd.isna(value):
        return ''
    value = str(value).strip().upper()
    return value if value not in ('—', 'N/A', 'NAN', '-') else ''


def _number(value):
    return pd.to_numeric(value, errors='coerce')


def enrich_membership_summary(company_summary: pd.DataFrame,
                              ranking_data: pd.DataFrame):
    """Return (summary sorted by USA universe final rank, detailed KPI table, counts).

    Matching prefers canonical company_key where it can be resolved; otherwise
    an *unambiguous* exact ticker is required. No company is dropped. N/A ranks
    always follow valid numeric ranks. No filtered-cohort ranking is calculated.
    """
    summary = company_summary.copy().reset_index(drop=True)
    if 'Ticker' not in summary:
        raise ValueError('Membership table needs a Ticker column')
    if 'Company' not in summary:
        raise ValueError('Membership table needs a Company column')
    ranks = ranking_data.copy()
    needed = {'ticker', 'final_rank', 'total_fundamental_rank', 'ranking_eligible'}
    if not needed.issubset(ranks.columns):
        raise ValueError('Fundamental ranking CSV is missing: ' + ', '.join(sorted(needed - set(ranks.columns))))
    ranks['__ticker'] = ranks['ticker'].map(_ticker)
    ranks = ranks[ranks['__ticker'].ne('')].copy()
    # Conflicting tickers may denote distinct issuers: do not silently choose.
    counts = ranks['__ticker'].value_counts()
    ranks = ranks[ranks['__ticker'].map(counts).eq(1)].set_index('__ticker', drop=False)
    summary['__ticker'] = summary['Ticker'].map(_ticker)
    reference = summary['__ticker'].map(ranks.to_dict('index'))
    # Pandas Series.map(dict) returns the row dict per unique ticker, if any.
    joined = pd.DataFrame(list(reference.map(lambda x: x if isinstance(x, dict) else {}).values), index=summary.index)
    def field(name):
        return joined[name] if name in joined else pd.Series(float('nan'), index=summary.index)
    eligible = field('ranking_eligible').astype(str).str.lower().isin(('true', 'yes', '1'))
    summary.insert(2, 'Final Rank', _number(field('final_rank')).where(eligible).astype('Int64'))
    summary.insert(3, 'Total Rank', _number(field('total_fundamental_rank')).where(eligible).astype('Int64'))
    reason = field('ranking_reason').fillna('No verified financial ranking')
    reason = reason.astype(str).replace({'nan': 'No verified financial ranking', '': 'No verified financial ranking'})
    summary.insert(4, 'Rank Status', reason)
    detailed = summary[['Company', 'Ticker', 'Final Rank', 'Total Rank', 'Rank Status']].copy()
    for col in METRICS:
        detailed[DISPLAY[col]] = _number(field(col))
        detailed[DISPLAY[col] + ' Rank'] = _number(field(col + '_rank')).astype('Int64')
    detailed['Market Cap (USD)'] = _number(field('market_cap'))
    detailed['Market Cap Tie Rank'] = _number(field('market_cap_rank')).astype('Int64')
    detailed['Financial Period'] = field('financial_period')
    order = summary.assign(__sort=summary['Final Rank'].fillna(10**12))
    idx = order.sort_values(['__sort', 'Company', 'Ticker'],
                            ascending=[True, True, True], kind='stable').index
    summary = summary.loc[idx].drop(columns=['__ticker']).reset_index(drop=True)
    detailed = detailed.loc[idx].reset_index(drop=True)
    return summary, detailed, {'matched': int(joined.get('final_rank', pd.Series(dtype=float)).notna().sum()),
                               'ranked': int(summary['Final Rank'].notna().sum()),
                               'total': len(summary)}


def load_usa_rankings():
    """Always re-read latest repository snapshot; cached caller may use mtime."""
    if not RANKINGS.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(RANKINGS, low_memory=False, dtype={'ticker': str, 'company_key': str})
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()
