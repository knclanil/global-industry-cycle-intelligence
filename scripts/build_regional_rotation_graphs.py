"""Regenerate Global, USA and India graph caches, including 13 NSE India sources.

Replace the existing scripts/build_regional_rotation_graphs.py with this file.
Must run after the regular constituent and price history refresh workflows.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from leading_lagging_engine import load_holdings, rotation_signals, build_lists, INDIA_SLUG_TICKERS
from rotation_graph_evidence import QUADRANTS, EDGE_COLUMNS, build_membership_edges
from india_index_rotation_expansion import SOURCE_TICKERS, build_extra_signals

OUT = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs'
PERIODS = {'1m': 21, '3m': 63, '6m': 126}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'built_utc': datetime.now(timezone.utc).isoformat(), 'regions': {}}
    # Register *exact* index slug -> internal price-source IDs for India holdings.
    # Without this registration, valid new NSE signals cannot become company edges.
    INDIA_SLUG_TICKERS.update(SOURCE_TICKERS)
    from stored_market_data import read_one
    try:
        india_benchmark = read_one('India', '^NSEI')
        extra_signals, diagnostics = build_extra_signals(india_benchmark, PERIODS.values())
    except Exception as exc:
        extra_signals = {days: pd.DataFrame() for days in PERIODS.values()}
        diagnostics = pd.DataFrame([{'status': 'unavailable', 'reason': f'{type(exc).__name__}: {exc}'}])
    diagnostics.to_csv(OUT / 'india_extra_index_history_status.csv', index=False)

    for region in ('Global', 'USA', 'India'):
        for period, days in PERIODS.items():
            key = f'{region.lower()}_{period}'
            stats = {'holdings_records': 0, 'rotation_signals': 0,
                     'membership_edges': 0, 'companies': 0,
                     'unmapped_sources': 0, 'error': None}
            try:
                holdings = load_holdings(region)
                signals = rotation_signals(region, days)
                if region == 'India':
                    addition = extra_signals.get(days, pd.DataFrame())
                    if not addition.empty:
                        signals = pd.concat([signals, addition], ignore_index=True)
                        # Same source ID should never occur twice in the graph.
                        signals = signals.drop_duplicates(['kind', 'source_id'], keep='first')
                stats['holdings_records'] = len(holdings)
                stats['rotation_signals'] = len(signals)
                if holdings.empty or signals.empty:
                    edges = pd.DataFrame(columns=EDGE_COLUMNS)
                    missing = pd.DataFrame(columns=['Source', 'Reason'])
                    lists = pd.DataFrame(columns=['Company', 'Ticker', 'company_key', 'Category', 'Score', 'Rank', 'Sector sources', 'Factor sources'])
                else:
                    edges, missing = build_membership_edges(region, holdings, signals)
                    lists, _ = build_lists(region, holdings, signals)
                stats['membership_edges'] = len(edges)
                stats['companies'] = edges['company_key'].nunique() if not edges.empty else 0
                stats['unmapped_sources'] = len(missing)
                for q in QUADRANTS:
                    stats[f'{q.lower()}_signals'] = int(signals['quadrant'].eq(q).sum()) if 'quadrant' in signals else 0
                    stats[f'{q.lower()}_companies'] = int(edges.loc[edges['quadrant'].eq(q), 'company_key'].nunique()) if not edges.empty else 0
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
