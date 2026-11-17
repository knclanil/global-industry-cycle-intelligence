"""Refresh historical prices in one Parquet file, retaining old observations on partial failures."""
from pathlib import Path
import sys
import pandas as pd
import yfinance as yf
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/prices.parquet'
config=pd.read_csv(ROOT/'config/instruments.csv').fillna('')
tickers=sorted(set(config.ticker)|set(config.benchmark))
old=pd.read_parquet(OUT) if OUT.exists() else pd.DataFrame(columns=['date','ticker','close'])
records=[]; failed=[]
for ticker in tickers:
 try:
  hist=yf.Ticker(ticker).history(period='max' if old.empty else '3mo',auto_adjust=True)
  if hist.empty or 'Close' not in hist: raise ValueError('no history returned')
  s=hist['Close'].dropna()
  for day,val in s.items(): records.append((str(day.date()),ticker,float(val)))
  print(ticker,len(s))
 except Exception as exc:
  failed.append({'ticker':ticker,'error':str(exc)[:250]});print('FAILED',ticker,str(exc)[:100])
if records:
 new=pd.DataFrame(records,columns=['date','ticker','close'])
 merged=pd.concat([old,new],ignore_index=True).drop_duplicates(['date','ticker'],keep='last')
 merged=merged.sort_values(['ticker','date']);merged.to_parquet(OUT,index=False)
 print('Saved',len(merged),'rows')
else:
 print('No new data; preserving existing history')
(ROOT/'data/collection_status.json').write_text(__import__('json').dumps({'attempted':len(tickers),'succeeded':len(tickers)-len(failed),'failed':failed,'run_utc':pd.Timestamp.utcnow().isoformat()},indent=2))
if not records and old.empty: sys.exit('No price data available; try again when provider is accessible')
