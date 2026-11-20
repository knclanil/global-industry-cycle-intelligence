"""Build complete four-quadrant knowledge graph caches for Global, USA and India.

Run after refreshing stored price histories and constituent/holdings datasets.
The graph membership CSV is intentionally independent from the strict
Leading/Lagging research lists.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from leading_lagging_engine import load_holdings, rotation_signals, build_lists
from rotation_graph_evidence import QUADRANTS, EDGE_COLUMNS, build_membership_edges

OUT = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs'
PERIODS = {'1m': 21, '3m': 63, '6m': 126}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'built_utc': datetime.now(timezone.utc).isoformat(), 'regions': {}}
    for region in ('Global', 'USA', 'India'):
        for period, days in PERIODS.items():
            key = f'{region.lower()}_{period}'
            stats = {'holdings_records': 0, 'rotation_signals': 0,
                     'membership_edges': 0, 'companies': 0,
                     'unmapped_sources': 0, 'error': None}
            try:
                holdings = load_holdings(region)
                signals = rotation_signals(region, days)
                stats['holdings_records'] = len(holdings)
                stats['rotation_signals'] = len(signals)
                if holdings.empty or signals.empty:
                    edges = pd.DataFrame(columns=EDGE_COLUMNS)
                    missing = pd.DataFrame(columns=['Source', 'Reason'])
                    lists = pd.DataFrame(columns=['Company', 'Ticker', 'company_key', 'Category', 'Score', 'Rank', 'Sector sources', 'Factor sources'])
                else:
                    edges, missing = build_membership_edges(region, holdings, signals)
                    # Preserve original strict research-list behavior; graph uses edges.
                    lists, _ = build_lists(region, holdings, signals)
                stats['membership_edges'] = len(edges)
                stats['companies'] = edges['company_key'].nunique() if not edges.empty else 0
                stats['unmapped_sources'] = len(missing)
                for q in QUADRANTS:
                    stats[f'{q.lower()}_signals'] = int(signals['quadrant'].eq(q).sum()) if 'quadrant' in signals else 0
                    stats[f'{q.lower()}_companies'] = int(edges.loc[edges['quadrant'].eq(q), 'company_key'].nunique()) if not edges.empty else 0
                # Publish each dataset only when the entire period build succeeds.
                edges.to_csv(OUT / f'{key}_edges.csv', index=False)
                signals.to_csv(OUT / f'{key}_signals.csv', index=False)
                lists.to_csv(OUT / f'{key}_companies.csv', index=False)
                missing.to_csv(OUT / f'{key}_unmapped.csv', index=False)
                stats['signal_asof'] = (sorted(signals['as_of'].dropna().unique().tolist())[-1]
                                        if 'as_of' in signals and not signals.empty else None)
            except Exception as exc:
                stats['error'] = f'{type(exc).__name__}: {exc}'
            report['regions'][key] = stats
    (OUT / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))
    return report

if __name__ == '__main__':
    build()
