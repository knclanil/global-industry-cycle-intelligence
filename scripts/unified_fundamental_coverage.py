#!/usr/bin/env python3
"""Cross-market, metric-level readiness report from published company research CSVs."""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
METRICS=('revenue','net_income','revenue_yoy','roe','operating_margin',
         'operating_cash_flow','free_cash_flow','debt_to_equity','price',
         'market_cap','pe','pb','research_score')
PATHS={'India': ROOT/'data'/'india_financials'/'opportunity_research.csv',
       'USA': ROOT/'data'/'usa_research'/'company_research.csv'}

def build_one(path):
    if not path.is_file():return {'status':'missing','companies':0,'metrics':{m:0 for m in METRICS}}
    df=pd.read_csv(path,low_memory=False)
    if 'company_key' not in df:raise ValueError(f'{path}: company_key column required')
    if df.company_key.isna().any() or df.company_key.astype(str).duplicated().any():
        raise ValueError(f'{path}: missing/duplicate company keys')
    metrics={m:int(pd.to_numeric(df[m],errors='coerce').notna().sum()) if m in df else 0 for m in METRICS}
    flags={name:int(df[name].astype(str).str.casefold().eq('yes').sum()) if name in df else 0
           for name in ('fundamental_ready','valuation_ready','research_ready')}
    return {'status':'available','companies':len(df),'metrics':metrics,'readiness':flags}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'data'/'research_coverage'/'fundamental_coverage.json')
    args=p.parse_args()
    report={'built_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            'markets':{market:build_one(path) for market,path in PATHS.items()},
            'notes':'Availability is not accuracy; missing data is never zero. Scores require suitable source periods, adequate peers and controls.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
