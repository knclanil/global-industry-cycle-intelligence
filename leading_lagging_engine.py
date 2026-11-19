"""Evidence-first sector × factor company lists, powered by saved relative rotation data.

'Leading' and 'Lagging' refer to benchmark-relative index performance only.
No inference of intrinsic value, investment opportunities, or company-price momentum.
Missing source price histories or absent sector/factor evidence never become zero scores.
"""
from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
MARKETS = {
    'Global': [('Global', 'sector', 'global_market_data'), ('GlobalFactors', 'factor', 'global_factor_market_data')],
    'USA': [('USA', 'sector', 'market_data'), ('USAFactors', 'factor', 'usa_factor_market_data')],
    'India': [('India', 'sector', 'india_market_data'), ('IndiaFactors', 'factor', 'india_factor_market_data')],
}
# NSE strategy names are not always identical to the market-price index labels.
# Exact, verified mapping; other factor and thematic indexes are not assigned a proxy.
INDIA_SLUG_TICKERS = {
    'nifty_bank': '^NIFTYBANK', 'nifty_psu_bank': '^CNXPSUBANK',
    'nifty_financial_services': '^NIFTYFIN_SERVICE', 'nifty_pharma': '^CNXPHARMA',
    'nifty_it': '^CNXIT', 'nifty_realty': '^CNXREALTY',
    'nifty_fmcg': '^CNXFMCG', 'nifty_metal': '^CNXMETAL',
    'nifty_auto': '^CNXAUTO', 'nifty_energy': '^CNXENERGY',
    'nifty_media': '^CNXMEDIA', 'nifty_infrastructure': '^CNXINFRA',
    'nifty50_value_20': 'NIFTY50_VALUE20',
    'nifty200_momentum_30': 'NIFTY200_MOMENTUM30',
    'nifty200_quality_30': 'NIFTY200_QUALITY30',
    'nifty100_low_volatility_30': 'NIFTY100_LOWVOL30',
    'nifty_alpha_index': 'NIFTY_ALPHA50',
    'nifty50_equal_weight': 'NIFTY50_EQUALWEIGHT',
}

def _clean(value):
    return re.sub(r'[^a-z0-9]+', '', str(value).lower())


def classify(rs: float, momentum: float) -> str:
    if not np.isfinite(rs) or not np.isfinite(momentum):
        return 'Unavailable'
    return ('Leading' if momentum >= 0 else 'Weakening') if rs >= 0 else ('Improving' if momentum >= 0 else 'Lagging')


def rotation_signals(region: str, lookback: int = 63) -> pd.DataFrame:
    """Compute comparable sector/factor performance from local validated close series only.

    The last comparable session is shared by each index and its benchmark; indices
    with older or insufficient series are excluded, never labeled lagging.
    """
    from importlib import import_module
    from stored_market_data import read_one
    out = []
    for market, kind, module_name in MARKETS[region]:
        module = import_module(module_name)
        benchmark = read_one(market, module.BENCHMARK)
        if benchmark.empty:
            continue
        bs = benchmark['Adj Close'].dropna()
        if bs.empty:
            continue
        for ticker, label in module.SECTORS.items():
            series = read_one(market, ticker)
            if series.empty:
                continue
            aligned = pd.concat([series['Adj Close'].rename('index'), bs.rename('benchmark')], axis=1).dropna().sort_index()
            aligned = aligned[(aligned['index'] > 0) & (aligned['benchmark'] > 0)]
            if len(aligned) < 2 * lookback + 1:
                continue
            # Avoid using stale constituent data as present-day market leadership.
            if (bs.index.max() - aligned.index.max()).days > 7:
                continue
            rel = aligned['index'] / aligned['benchmark']
            rs = 100 * (rel.iloc[-1] / rel.iloc[-1 - lookback] - 1)
            past_rs = 100 * (rel.iloc[-1 - lookback // 2] / rel.iloc[-1 - lookback // 2 - lookback] - 1)
            mom = rs - past_rs
            quadrant = classify(float(rs), float(mom))
            out.append(dict(region=region, kind=kind, source_id=ticker, label=label,
                            relative_strength=round(float(rs), 3), rs_momentum=round(float(mom), 3),
                            quadrant=quadrant, as_of=str(aligned.index[-1].date()),
                            source='Repository market history'))
    return pd.DataFrame(out)


# Sector and factor reference ETFs are market proxies, NOT necessarily the same
# iShares ETF used for holdings. Matching is based on issuer-provided fund title;
# ambiguous names are deliberately left unmapped. Explicit mappings take priority.
SECTOR_KEYWORDS = [
    ('Communication Services', ('communication services', 'communications sector', 'telecommunication')),
    ('Consumer Discretionary', ('consumer discretionary',)),
    ('Consumer Staples', ('consumer staples',)),
    ('Financials', ('financials', 'financial sector', 'financial services')),
    ('Healthcare', ('healthcare', 'health care')),
    ('Technology', ('information technology', 'technology sector', 'u.s. technology', 'global tech')),
    ('Industrials', ('industrials', 'industrial sector')),
    ('Materials', ('materials', 'basic materials')),
    ('Real Estate', ('real estate', 'reit')),
    ('Utilities', ('utilities', 'utility sector')),
    ('Energy', ('energy sector', 'global energy', 'u.s. energy')),
]
FACTOR_KEYWORDS = [
    ('Minimum Volatility', ('minimum volatility', 'min vol', 'low volatility', 'min volatility')),
    ('Momentum', ('momentum',)),
    ('Quality', ('quality',)),
    ('Value', ('value factor', 'value etf', 'value index', 'msci value', 's&p 500 value', 'russell 1000 value')),
    ('Growth', ('growth factor', 'growth etf', 'growth index', 'msci growth', 's&p 500 growth', 'russell 1000 growth')),
    ('Dividend Yield', ('dividend yield', 'high dividend', 'dividend select', 'dividend growth')),
    ('Small Cap', ('small cap', 'small-cap', 'size factor')),
    ('Size', ('size factor', 'small cap', 'small-cap')),
]

def _title_proxy(title: str, kind: str, signals: pd.DataFrame):
    """A transparent category *proxy*; never implies portfolio-price identity."""
    title = re.sub(r'\s+', ' ', str(title).lower()).strip()
    if not title or title in ('nan','none'): return None
    # Do not map broad/multi-sector ETFs as if they were a pure factor/sector.
    if any(bad in title for bad in ('multi-factor', 'multifactor', 'multi sector', 'multi-sector')):
        return None
    rules = SECTOR_KEYWORDS if kind == 'sector' else FACTOR_KEYWORDS
    matches = [family for family, keys in rules if any(k in title for k in keys)]
    # Size is called 'Small Cap' in the USA price universe, and 'Size' globally.
    if set(matches) == {'Small Cap','Size'}:
        matches = ['Small Cap'] if (signals['label'].str.casefold() == 'small cap').any() else ['Size']
    if len(set(matches)) != 1: return None
    family = matches[0]
    candidates = signals[(signals['kind'] == kind) & (signals['label'].str.casefold() == family.casefold())]
    if len(candidates) != 1: return None
    row = candidates.iloc[0].to_dict()
    row['mapping_method'] = 'category_proxy'
    row['mapping_note'] = f"{title} → {family} reference ETF (NOT the source fund price)"
    return row


def source_signal_mapping(region: str, holdings: pd.DataFrame, signals: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Map exact official portfolio/index identity where possible; don't guess ambiguous names."""
    if signals.empty:
        return {}, []
    matches, skipped = {}, []
    if region == 'India':
        from india_constituents import INDEX_BY_SLUG
        lookup = signals.set_index('source_id')
        for slug, definition in INDEX_BY_SLUG.items():
            ticker = INDIA_SLUG_TICKERS.get(slug)
            if ticker and ticker in lookup.index:
                row = lookup.loc[ticker]
                if isinstance(row, pd.DataFrame): row = row.iloc[0]
                if row['kind'] == ('factor' if definition.category in ('Factor', 'Strategy') else 'sector'):
                    matches[slug] = row.to_dict()
            if slug not in matches:
                skipped.append({'Source': definition.name, 'Reason': 'No verified matching rotation signal'})
    else:
        # Optional audited explicit mapping remains highest priority.
        mapping_path = DATA / 'market' / 'rotation_source_links.csv'
        if mapping_path.is_file():
            links = pd.read_csv(mapping_path, dtype=str).fillna('')
            required = {'region', 'source_id', 'market_ticker', 'kind'}
            if required.issubset(links.columns):
                lookup = {(str(r.kind).lower(), r.source_id): r for r in signals.itertuples(index=False)}
                for row in links.itertuples(index=False):
                    if row.region.strip().upper() != region.upper(): continue
                    kind = row.kind.lower().strip()
                    if (kind, row.market_ticker) in lookup:
                        match = lookup[(kind, row.market_ticker)]._asdict()
                        match['mapping_method'] = 'explicit'
                        match['mapping_note'] = 'Operator-provided source → price series mapping'
                        matches[row.source_id] = match
        # Independently support category-proxy rotation for the iShares holdings
        # funds already downloaded. This avoids a wholly blank USA/Global page
        # when the optional explicit mapping file contains only a header.
        if {'portfolio_id','fund_title'}.issubset(holdings.columns):
            for pid, grp in holdings.groupby(holdings.portfolio_id.astype(str), sort=False):
                if pid in matches: continue
                expected_kind = 'sector' if pid in (set(__import__('holdings_intelligence').SECTORS) |
                                     set(__import__('holdings_intelligence').GLOBAL_SECTORS)) else 'factor'
                titles = [str(t).strip() for t in grp['fund_title'].dropna().unique() if str(t).strip()]
                if len(titles) != 1:
                    skipped.append({'Source':pid,'Fund': ' / '.join(titles[:2]), 'Reason':'Missing or ambiguous issuer fund title'})
                    continue
                proxy = _title_proxy(titles[0], expected_kind, signals)
                if proxy is None:
                    skipped.append({'Source':pid,'Fund':titles[0], 'Reason':'No unambiguous category proxy with valid price history'})
                else:
                    matches[pid] = proxy
        for pid in sorted(holdings.portfolio_id.astype(str).unique()) if not holdings.empty else []:
            if pid not in matches and not any(r['Source'] == pid for r in skipped):
                skipped.append({'Source':pid, 'Reason':'No valid source → rotation series mapping'})
    return matches, skipped


def _as_rows(holdings):
    if holdings.empty: return []
    return holdings.to_dict('records')


def build_lists(region: str, holdings: pd.DataFrame, signals: pd.DataFrame, *, min_sector=1, min_factor=1):
    """Leading/Lagging require sector AND factor observations in same quadrant.

    For weighted iShares portfolios, within-side score is conviction-scaled
    and based on verified exposure; for NSE, source membership is unweighted.
    Final values are ordinal evidence strengths, NOT return forecasts.
    """
    mapping, missing = source_signal_mapping(region, holdings, signals)
    aggregated = {}
    for r in _as_rows(holdings):
        pid = str(r.get('index_slug' if region == 'India' else 'portfolio_id', ''))
        signal = mapping.get(pid)
        if signal is None or signal['quadrant'] not in ('Leading', 'Lagging'):
            continue
        kind = signal['kind']
        company_id = str(r.get('company_key' if region == 'India' else 'issuer_id', '')).strip()
        if not company_id: continue
        side = signal['quadrant']
        key = (company_id, side)
        row = aggregated.setdefault(key, dict(company_key=company_id, company=str(r.get('company_name' if region=='India' else 'company', '')),
                      ticker=str(r.get('symbol' if region=='India' else 'ticker','')), side=side,
                      sector={}, factor={}, sector_names=set(), factor_names=set()))
        # Deduplicate original company-index pairs; carry true weights when available.
        exposure = 1.0
        if region != 'India':
            try:
                exposure = float(r.get('weight'))
            except (TypeError, ValueError):
                continue
            if not (0 <= exposure <= 100): continue
        if pid not in row[kind]:
            row[kind][pid] = (exposure, signal)
            row[kind + '_names'].add(str(signal['label']))
    rows = []
    for (_, _), r in aggregated.items():
        ns, nf = len(r['sector']), len(r['factor'])
        if ns < min_sector or nf < min_factor: continue
        def strength(evidence):
            if not evidence: return None
            # Rank on relative trend magnitude only among matched sources;
            # exposure is a secondary tie-breaker for iShares, not fabricated NSE weight.
            return float(np.mean([abs(float(s['relative_strength'])) + 0.5 * abs(float(s['rs_momentum']))
                                   for w, s in evidence.values()]))
        sec = strength(r['sector']); fac = strength(r['factor'])
        if sec is None or fac is None: continue
        # Geometric mean favors strength on BOTH dimensions. Small breadth bonus.
        strength_score = np.sqrt(sec * fac) + min(ns + nf - 2, 6) * 0.15
        rows.append(dict(Company=r['company'], Ticker=r['ticker'], company_key=r['company_key'],
                         Category=r['side'], Score=round(float(strength_score), 3),
                         **{'Sector indices': ns, 'Factor indices': nf,
                            'Sector RS magnitude':round(sec, 2), 'Factor RS magnitude': round(fac, 2),
                            'Sector sources': ' · '.join(sorted(r['sector_names'])),
                            'Factor sources': ' · '.join(sorted(r['factor_names'])),
                            'Signal basis': 'Category ETF proxy' if any(s.get('mapping_method') == 'category_proxy' for _,s in (*r['sector'].values(), *r['factor'].values())) else 'Direct source mapping',
                            'Exposure': round(sum(v[0] for v in (*r['sector'].values(), *r['factor'].values())), 3) if region!='India' else None}))
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(['Category','Score','Sector indices','Factor indices','Ticker'],
                                  ascending=[True,False,False,False,True]).reset_index(drop=True)
        frame['Rank'] = frame.groupby('Category')['Score'].rank(method='min', ascending=False).astype(int)
    return frame, pd.DataFrame(missing)


def load_holdings(region: str) -> pd.DataFrame:
    if region == 'India':
        path = DATA / 'india_holdings' / 'constituents.csv'
        return pd.read_csv(path, dtype=str).fillna('') if path.exists() else pd.DataFrame()
    path = DATA / 'holdings' / 'latest_holdings.parquet'
    if not path.exists(): return pd.DataFrame()
    holdings = pd.read_parquet(path)
    import holdings_intelligence as h
    ids = set(h.GLOBAL_FACTORS+h.GLOBAL_SECTORS) if region=='Global' else set(h.FACTORS+h.SECTORS)
    return holdings[holdings.portfolio_id.astype(str).isin(ids)].copy()
