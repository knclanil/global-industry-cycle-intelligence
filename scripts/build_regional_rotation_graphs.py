"""Materialize market-leading / lagging company networks outside Streamlit.

Run after price-history and holdings refresh. Never infer weak companies from
missing market prices. Separate region and lookback; preserve dates and sources.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from leading_lagging_engine import load_holdings, rotation_signals, build_lists

OUT=ROOT/'data'/'dashboard_cache'/'rotation_graphs'
PERIODS={'1m':21,'3m':63,'6m':126}

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    report={"built_utc":datetime.now(timezone.utc).isoformat(),"regions":{}}
    for region in ('Global','USA','India'):
        for period,days in PERIODS.items():
            key=f'{region.lower()}_{period}'
            stats={'holdings_records':0,'rotation_signals':0,'leading_companies':0,'lagging_companies':0,
                   'unmapped_sources':0,'error':None}
            try:
                holdings=load_holdings(region)
                stats['holdings_records']=len(holdings)
                signals=rotation_signals(region,days)
                stats['rotation_signals']=len(signals)
                if holdings.empty or signals.empty:
                    results=pd.DataFrame(columns=['Company','Ticker','company_key','Category','Score','Rank','Sector sources','Factor sources'])
                    missing=pd.DataFrame()
                else:
                    results,missing=build_lists(region,holdings,signals)
                stats['unmapped_sources']=len(missing)
                if not results.empty:
                    stats['leading_companies']=int(results.Category.eq('Leading').sum())
                    stats['lagging_companies']=int(results.Category.eq('Lagging').sum())
                results.to_csv(OUT/f'{key}_companies.csv',index=False)
                signals.to_csv(OUT/f'{key}_signals.csv',index=False)
                missing.to_csv(OUT/f'{key}_unmapped.csv',index=False)
                stats['signal_asof']=sorted(signals['as_of'].dropna().unique().tolist())[-1] if 'as_of' in signals and not signals.empty else None
            except Exception as exc:
                # Do not overwrite a last-good dataset with an empty output on failure.
                stats['error']=f'{type(exc).__name__}: {exc}'
            report['regions'][key]=stats
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report
if __name__=='__main__':build()
