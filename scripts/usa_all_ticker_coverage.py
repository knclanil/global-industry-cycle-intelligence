#!/usr/bin/env python3
"""Audit every verified USA ticker; preserve missingness, report collection progress."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def main():
    from sys import path
    path.insert(0,str(ROOT))
    from usa_research_data import STORE,build_memberships
    from usa_sec_cache_reader import ticker_directory
    holdings=STORE/'latest_holdings.parquet'
    if not holdings.exists():raise SystemExit(f'Missing verified holdings: {holdings}')
    members=build_memberships(pd.read_parquet(holdings))
    if members.empty:raise SystemExit('Verified USA universe empty')
    directory=ticker_directory(ROOT)
    qpath=ROOT/'data/usa_research/quotes.csv'
    quotes=pd.read_csv(qpath,dtype={'ticker':str}).fillna('') if qpath.exists() else pd.DataFrame()
    qmap={str(r['ticker']).upper():r for r in quotes.to_dict('records')} if 'ticker' in quotes else {}
    rpath=ROOT/'data/usa_research/fundamental_rankings.csv'
    ranked=pd.read_csv(rpath,dtype={'ticker':str}).fillna('') if rpath.exists() else pd.DataFrame()
    rankmap={str(r['company_key']):r for r in ranked.to_dict('records')} if 'company_key' in ranked else {}
    rows=[]
    for r in members.to_dict('records'):
        ticker=str(r.get('ticker','')).strip().upper()
        cik=directory.get(ticker.replace('.','-'))
        cached=bool(cik is not None and any(p.exists() for p in (ROOT/f'data/fundamentals/facts_{cik:010d}.json',ROOT/f'data/sec_cache/CIK{cik:010d}.json')))
        quote=qmap.get(ticker,{})
        ranking=rankmap.get(str(r.get('company_key')),{})
        def valid(v):
            return v is not None and str(v).strip().lower() not in ('','nan','none','null','<na>')
        metrics=['roe','current_ratio','operating_margin','net_margin','eps_growth_pct']
        present=sum(valid(ranking.get(m)) for m in metrics)
        rows.append({'company_key':r.get('company_key'),'company':r.get('company'),'ticker':ticker,
                     'sec_cik':cik,'sec_cached':cached,'kpi_fields_available':present,
                     'all_five_kpis':present==5,'has_price':valid(quote.get('price')),
                     'has_market_cap':valid(quote.get('market_cap')),
                     'final_rank':ranking.get('final_rank',''),
                     'coverage_status':('complete' if present==5 else 'partial' if present else 'missing'),
                     'missing_kpis':'; '.join(m for m in metrics if not valid(ranking.get(m)))})
    output=ROOT/'data/usa_research';output.mkdir(parents=True,exist_ok=True)
    frame=pd.DataFrame(rows)
    frame.to_csv(output/'all_ticker_financial_coverage.csv',index=False)
    report={'built_utc':datetime.now(timezone.utc).isoformat(),'verified_company_records':len(frame),
            'unique_tickers':int(frame.ticker.nunique()),'sec_cik_mapped':int(frame.sec_cik.notna().sum()),
            'sec_companyfacts_cached':int(frame.sec_cached.sum()),
            'all_five_kpis':int(frame.all_five_kpis.sum()),
            'partial_kpis':int(((frame.kpi_fields_available>0)&(frame.kpi_fields_available<5)).sum()),
            'no_kpis':int((frame.kpi_fields_available==0).sum()),
            'has_price':int(frame.has_price.sum()),'has_market_cap':int(frame.has_market_cap.sum()),
            'unmapped_tickers':sorted(frame.loc[frame.sec_cik.isna(),'ticker'].unique().tolist()),
            'note':'Coverage is not completeness; SEC filing data may be unavailable or not comparable. Missing data is not zero.'}
    (output/'all_ticker_financial_coverage.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='unmapped_tickers'},indent=2))
if __name__=='__main__':main()
