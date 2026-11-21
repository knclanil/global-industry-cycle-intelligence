"""Evidence-first graph snapshots; separate from Leading/Lagging ranking filters.

A graph edge says that a company belongs to a verified, mapped sector/factor
portfolio/index. It does NOT assert that the company's own stock has that
rotation classification.
"""
from __future__ import annotations

import pandas as pd

QUADRANTS = ('Leading', 'Improving', 'Weakening', 'Lagging')
EDGE_COLUMNS = ['company_key', 'Company', 'Ticker', 'quadrant', 'kind',
                'source_id', 'label', 'mapping_method', 'mapping_note',
                'portfolio_id', 'weight']


def build_membership_edges(region: str, holdings: pd.DataFrame,
                           signals: pd.DataFrame):
    """Return all qualifying membership edges plus mapping diagnostics.

    Retains sector-only or factor-only companies. No top-N selection and no
    requirement for both kinds of evidence. Signal nodes are sourced separately
    from `signals`, so valid unconnected sector/factor signals remain visible.
    """
    from leading_lagging_engine import source_signal_mapping
    if holdings.empty:
        return pd.DataFrame(columns=EDGE_COLUMNS), pd.DataFrame()
    mapping, unmapped = source_signal_mapping(region, holdings, signals) if not signals.empty else ({}, [])
    # An official index constituent can establish FACTOR MEMBERSHIP even when
    # its market-price history cannot establish rotation. Never invent a quadrant.
    if region == 'India':
        from india_index_rotation_expansion import SOURCE_TICKERS
        growth_slug = 'nifty500_growth_50'
        if growth_slug not in mapping:
            mapping[growth_slug] = {
                'quadrant': 'Unavailable', 'kind': 'factor',
                'source_id': SOURCE_TICKERS[growth_slug], 'label': 'Growth',
                'mapping_method': 'official_constituent_membership',
                'mapping_note': 'Constituents verified; index rotation unavailable. No price signal inferred.',
            }
            # This is a missing rotation, not a missing category or membership.
            unmapped = [r for r in unmapped if
                        str(r.get('Source', '')).casefold().replace(' ', '') not in
                        ('nifty500growth50',)]
    records = []
    for item in holdings.to_dict('records'):
        pid = str(item.get('index_slug' if region == 'India' else 'portfolio_id', '')).strip()
        signal = mapping.get(pid)
        if not signal or signal.get('quadrant') not in (*QUADRANTS, 'Unavailable'):
            continue
        kind = str(signal.get('kind', '')).strip().lower()
        if kind not in ('sector', 'factor'):
            continue
        company_key = str(item.get('company_key' if region == 'India' else 'issuer_id', '')).strip()
        if not company_key or company_key.lower() in ('nan', 'none'):
            continue
        weight = None
        if region != 'India':
            weight = pd.to_numeric(item.get('weight'), errors='coerce')
            if pd.isna(weight) or not 0 <= float(weight) <= 100:
                continue
        records.append({
            'company_key': company_key,
            'Company': str(item.get('company_name' if region == 'India' else 'company', '')).strip(),
            'Ticker': str(item.get('symbol' if region == 'India' else 'ticker', '')).strip(),
            'quadrant': str(signal['quadrant']),
            'kind': kind,
            'source_id': str(signal['source_id']),
            'label': str(signal['label']),
            'mapping_method': str(signal.get('mapping_method', 'exact')),
            'mapping_note': str(signal.get('mapping_note', '')),
            'portfolio_id': pid,
            'weight': float(weight) if weight is not None else None,
        })
    df = pd.DataFrame(records, columns=EDGE_COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=['company_key', 'quadrant', 'kind', 'source_id', 'portfolio_id'])
    return df, pd.DataFrame(unmapped)


def graph_elements(signals: pd.DataFrame, edges: pd.DataFrame):
    """Build all four rotation nodes, every valid index signal, and all mapped companies."""
    nodes = [{'id': f'q:{q}', 'label': q, 'type': 'rotation', 'quadrant': q}
             for q in QUADRANTS]
    links = set()
    by_id = {node['id']: node for node in nodes}
    if not signals.empty:
        expected = {'quadrant', 'kind', 'source_id', 'label'}
        if expected.issubset(signals.columns):
            for s in signals.to_dict('records'):
                q, kind, source = str(s['quadrant']), str(s['kind']), str(s['source_id'])
                if q not in QUADRANTS or kind not in ('sector', 'factor') or not source:
                    continue
                nid = f'i:{q}:{kind}:{source}'
                if nid not in by_id:
                    by_id[nid] = {'id': nid, 'label': str(s['label']), 'type': kind,
                                  'quadrant': q, 'source_id': source,
                                  'rs': s.get('relative_strength'),
                                  'momentum': s.get('rs_momentum')}
                    nodes.append(by_id[nid])
                links.add((f'q:{q}', nid))
    if not edges.empty:
        expected = {'company_key', 'Company', 'Ticker', 'quadrant', 'kind', 'source_id'}
        if expected.issubset(edges.columns):
            for e in edges.to_dict('records'):
                index_id = f"i:{e['quadrant']}:{e['kind']}:{e['source_id']}"
                if index_id not in by_id:
                    if (str(e['quadrant']) == 'Unavailable' and str(e['kind']) == 'factor'
                            and str(e.get('mapping_method', '')) == 'official_constituent_membership'):
                        # The factor index itself is known; only its ROTATION is unavailable.
                        # Do not connect this node to a rotation quadrant.
                        by_id[index_id] = {'id': index_id, 'type': 'factor',
                                           'label': str(e.get('label', 'Growth')),
                                           'quadrant': 'Unavailable',
                                           'source_id': str(e['source_id']),
                                           'rs': None, 'momentum': None}
                        nodes.append(by_id[index_id])
                    else:
                        continue
                company_id = f"c:{e['company_key']}"
                if company_id not in by_id:
                    by_id[company_id] = {'id': company_id, 'type': 'company',
                                         'label': str(e['Ticker']) or str(e['Company']) or str(e['company_key']),
                                         'name': str(e['Company']), 'company_key': str(e['company_key'])}
                    nodes.append(by_id[company_id])
                links.add((index_id, company_id))
    return nodes, sorted(links)
