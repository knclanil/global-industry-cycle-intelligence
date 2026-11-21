"""Evidence-first Global Capital Network model.

One canonical row set, one edge set, no inferred company membership. Country
rotation is relative to ACWI. The Global breadth score is an explicitly
*equal-weighted coverage indicator*, not a capital-flow or ACWI performance score.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

COUNTRIES = {
    'SPY': 'United States', 'INDA': 'India', 'EWJ': 'Japan',
    'MCHI': 'China', 'EWU': 'United Kingdom', 'EWG': 'Germany',
    'EWQ': 'France', 'EWL': 'Switzerland', 'EWC': 'Canada',
    'EWA': 'Australia', 'EWY': 'South Korea', 'EWT': 'Taiwan',
    'EWZ': 'Brazil', 'EWW': 'Mexico', 'EZA': 'South Africa',
    'EIDO': 'Indonesia', 'THD': 'Thailand', 'EWM': 'Malaysia',
    'KSA': 'Saudi Arabia', 'UAE': 'United Arab Emirates',
}
REGIONS = {'usa': ('United States','SPY'), 'india': ('India','INDA'),
           'global': ('Global direct','')}
ROTATIONS = ('Leading', 'Improving', 'Weakening', 'Lagging')
ROUTE = ('Global', 'Rotation', 'Country', 'Sector', 'Company', 'Factor')
ALL = list(ROUTE) + ['scope', 'country_etf', 'sector_id', 'company_id',
    'factor_id', 'sector_rotation', 'factor_rotation', 'company_name',
    'evidence', 'as_of', 'relative_strength', 'momentum']


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False).fillna('')
    except (ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def clean(x):
    return str(x if x is not None else '').strip()


def build_model(period: str, cache: Path) -> tuple[pd.DataFrame, dict]:
    """Produce canonical paths from country rotation, signal, and edge CSVs.

    A blank dimension is missing evidence, never a negative assertion.
    Global-direct uses a clearly identified scope, not a made-up country ETF.
    """
    if period not in ('1m', '3m', '6m'):
        raise ValueError('period must be 1m/3m/6m')
    rotations = read_csv(cache / f'country_{period}_rotations.csv')
    country_q = {}
    country_metrics = {}
    if {'ETF', 'Quadrant'} <= set(rotations):
        for r in rotations.to_dict('records'):
            ticker = clean(r.get('ETF')).upper()
            q = clean(r.get('Quadrant'))
            if ticker in COUNTRIES and q in ROTATIONS:
                country_q[ticker] = q
                country_metrics[ticker] = {
                    'as_of': clean(r.get('As of')),
                    'relative_strength': clean(r.get('Relative strength (%)')),
                    'momentum': clean(r.get('RS momentum (pp)'))}
    rows = []
    def put(q, country, scope, etf='', sector='', company='', factor='', **kw):
        base = dict.fromkeys(ALL, '')
        base.update({'Global': 'Global', 'Rotation': q, 'Country': country,
                     'Sector': sector, 'Company': company, 'Factor': factor,
                     'scope': scope, 'country_etf': etf})
        base.update(country_metrics.get(etf, {}))
        base.update(kw)
        rows.append(base)

    for etf, country in COUNTRIES.items():
        scope = 'usa' if etf == 'SPY' else 'india' if etf == 'INDA' else etf
        put(country_q.get(etf, 'Unclassified'), country, scope, etf,
            evidence='country-rotation-only')

    # Global data must use a separate scope; country membership is not inferred.
    put('Global scope', 'Global direct', 'global', evidence='global-scope')
    diagnostic = {'tracked_countries': len(COUNTRIES),
                  'classified_countries': len(country_q), 'period': period}
    for region, (country, etf) in REGIONS.items():
        q = country_q.get(etf, 'Unclassified') if etf else 'Global scope'
        signals = read_csv(cache / f'{region}_{period}_signals.csv')
        links = read_csv(cache / f'{region}_{period}_edges.csv')
        if not {'source_id', 'kind', 'label'} <= set(signals):
            diagnostic[f'{region}_signals'] = 'missing or invalid'
            continue
        evidence = {}
        for r in signals.to_dict('records'):
            kind, sid = clean(r.get('kind')).lower(), clean(r.get('source_id'))
            if kind in ('sector', 'factor') and sid:
                evidence[(kind,sid)] = (clean(r.get('label')) or sid,
                    clean(r.get('quadrant')).title())
        companies = defaultdict(lambda: {'sectors': {}, 'factors': {},
                                         'ticker': '', 'name': ''})
        mapped = set()
        if {'source_id', 'kind', 'company_key'} <= set(links):
            for r in links.to_dict('records'):
                kind, sid = clean(r.get('kind')).lower(), clean(r.get('source_id'))
                cid = clean(r.get('company_key'))
                if (kind,sid) not in evidence or not cid:
                    continue
                c = companies[cid]
                c['ticker'] = clean(r.get('Ticker')) or c['ticker']
                c['name'] = clean(r.get('Company')) or c['name']
                c['sectors' if kind == 'sector' else 'factors'][sid] = evidence[(kind,sid)]
                mapped.add((kind,sid))
        else:
            diagnostic[f'{region}_edges'] = 'missing or invalid'
        for cid, details in companies.items():
            sectors = list(details['sectors'].items()) or [('', ('', ''))]
            factors = list(details['factors'].items()) or [('', ('', ''))]
            label = details['ticker'] or details['name'] or cid
            # Combine only memberships of *the same verified company ID*.
            for sid, (sname, sq) in sectors:
                for fid, (fname, fq) in factors:
                    put(q, country, region, etf, sname, label, fname,
                        sector_id=f'{region}:sector:{sid}' if sid else '',
                        company_id=f'{region}:company:{cid}',
                        factor_id=f'{region}:factor:{fid}' if fid else '',
                        sector_rotation=sq, factor_rotation=fq,
                        company_name=details['name'], evidence=(
                        'sector+factor' if sid and fid else
                        'sector-only' if sid else 'factor-only'))
        # Signals with no company evidence still have a verified country/scope.
        for (kind, sid), (label, sq) in evidence.items():
            if (kind,sid) in mapped:
                continue
            put(q, country, region, etf,
                sector=label if kind == 'sector' else '',
                factor=label if kind == 'factor' else '',
                sector_id=f'{region}:sector:{sid}' if kind == 'sector' else '',
                factor_id=f'{region}:factor:{sid}' if kind == 'factor' else '',
                sector_rotation=sq if kind == 'sector' else '',
                factor_rotation=sq if kind == 'factor' else '',
                evidence='signal-only')
        diagnostic[f'{region}_companies'] = len(companies)
    return pd.DataFrame(rows, columns=ALL).drop_duplicates(), diagnostic


def global_breadth_score(table: pd.DataFrame) -> dict:
    """Equal-weighted breadth (0-100), NOT a capital-weighted global market score.

    Leading=100, Improving=66.67, Weakening=33.33, Lagging=0.
    Unclassified countries excluded; coverage is always reported.
    """
    countries = table[table.country_etf.ne('')][['country_etf', 'Rotation']].drop_duplicates('country_etf')
    weight = {'Leading':100., 'Improving':200/3, 'Weakening':100/3, 'Lagging':0.}
    valid = countries[countries.Rotation.isin(weight)]
    return {'score': round(valid.Rotation.map(weight).mean(), 1) if len(valid) else None,
            'classified': len(valid), 'tracked': len(COUNTRIES),
            'method': 'Equal-weighted rotation breadth, NOT ACWI return/capital flow'}


def filter_model(table, rotations=(), countries=(), sectors=(), companies=(),
                 factors=(), matching='Any'):
    """OR within dimensions, AND between dimensions; cross-membership ALL.

    When a filter is applied, country-only and unrelated records disappear.
    Other verified memberships of matching companies remain shown, enabling
    a path from selected sector through company to other factor memberships.
    """
    df = table.copy()
    for col, values in (('Rotation',rotations), ('Country',countries)):
        if values:
            df = df[df[col].isin(values)]
    if companies:
        df = df[df.company_id.isin(companies)]
    sets = ([set(df.loc[df.sector_id.eq(s),'company_id']) - {''} for s in sectors] +
            [set(df.loc[df.factor_id.eq(f),'company_id']) - {''} for f in factors])
    if sets:
        matches = set.intersection(*sets) if matching == 'All' else set.union(*sets)
        df = df[df.company_id.isin(matches)]
    if any((rotations,countries,sectors,companies,factors)):
        # Drop diagnostic-only rows unless they were explicitly selected by
        # country/rotation with no finer-grained filter.
        if sectors or companies or factors:
            df = df[df.company_id.ne('')]
    return df


def to_graph(table: pd.DataFrame, *, include_gaps: bool = True,
             show_empty_rotations: bool = True):
    """Build adjacency only. Evidence gaps are explicit, never fabricated.

    Returns nodes, edges. Edges have an `evidence` flag; missing-sector
    bridges are UI-only, dashed, and labelled 'No verified sector'.
    """
    nodes = {'global': {'layer':0, 'label':'GLOBAL', 'kind':'Global', 'rotation':''}}
    # Display missing quadrants without inventing a country or relationship.
    # When filters are active, callers disable this to hide unrelated nodes.
    if show_empty_rotations:
        for quadrant in ROTATIONS:
            nodes[f'rotation:{quadrant}'] = {
                'layer': 1, 'label': quadrant, 'kind': 'Rotation',
                'rotation': quadrant, 'empty': True,
            }
    edges = {}
    def node(key, layer, label, kind, rotation='', **meta):
        nodes[key] = {'layer':layer, 'label':label, 'kind':kind,
                      'rotation':rotation, **meta}
    def edge(a,b,verified=True):
        if a in nodes and b in nodes:
            edges[(a,b)] = bool(verified)
    for r in table.to_dict('records'):
        q, country, scope = r['Rotation'], r['Country'], r['scope']
        if not q or not country:
            continue
        rot = f'rotation:{q}'
        cid = f'country:{scope}'
        node(rot, 1, q, 'Rotation', q, empty=False)
        node(cid, 2, country, 'Country', q,
             rs=r['relative_strength'], momentum=r['momentum'],
             as_of=r['as_of'])
        edge('global', rot)
        edge(rot, cid)
        if r['sector_id']:
            sid = r['sector_id']
            node(sid,3,r['Sector'],'Sector',r['sector_rotation'],scope=scope)
            edge(cid,sid)
        elif r['company_id'] and include_gaps:
            sid = f'{cid}:unverified-sector'
            node(sid,3,'Sector not verified','Gap','',scope=scope)
            edge(cid,sid,False)
        else:
            sid = ''
        if r['company_id']:
            company_id = r['company_id']
            node(company_id,4,r['Company'],'Company','',scope=scope,
                 full_name=r['company_name'])
            edge(sid,company_id, bool(r['sector_id']))
        if r['factor_id']:
            fid = r['factor_id']
            node(fid,5,r['Factor'],'Factor',r['factor_rotation'],scope=scope)
            if r['company_id']:
                edge(r['company_id'],fid)
            # Factor without company evidence has no invented membership edge.
    return nodes, [{'source':a,'target':b,'verified':v}
                   for (a,b),v in sorted(edges.items())]


def validate_model(table: pd.DataFrame, nodes: dict, edges: list) -> list[str]:
    errors = []
    if table.empty:
        errors.append('No path records')
    if not {'global'} <= set(nodes):
        errors.append('Global root missing')
    for e in edges:
        a,b = e['source'],e['target']
        if a not in nodes or b not in nodes:
            errors.append('Edge references missing node')
        elif nodes[b]['layer'] != nodes[a]['layer']+1:
            errors.append('Non-adjacent edge')
    for q in table.Rotation.unique():
        if ('global',f'rotation:{q}') not in {(e['source'],e['target']) for e in edges}:
            errors.append(f'Global root disconnected from {q}')
    return sorted(set(errors))
