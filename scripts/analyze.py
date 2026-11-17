"""Price-based market-cycle estimates; no claims about fundamental business-cycle stage."""
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data/prices.parquet'
if not P.exists(): raise SystemExit('Run collect_prices.py first')
prices=pd.read_parquet(P); prices['date']=pd.to_datetime(prices.date)
config=pd.read_csv(ROOT/'config/instruments.csv').fillna('')
wide=prices.pivot(index='date',columns='ticker',values='close').sort_index()
# Resample to month-end, preserving actual last available close.
monthly=wide.resample('ME').last()
outputs=[];history=[]
for row in config.itertuples(index=False):
 if row.ticker not in monthly or row.benchmark not in monthly:continue
 both=monthly[[row.ticker,row.benchmark]].dropna()
 if len(both)<8:continue
 s=both[row.ticker];b=both[row.benchmark]
 # Relative price ratio (normalized). Difference of returns used for rankings.
 ratio=s/b
 rs6=(s/s.shift(6)-b/b.shift(6))*100
 rs3=(s/s.shift(3)-b/b.shift(3))*100
 rs1=(s/s.shift(1)-b/b.shift(1))*100
 rs12=(s/s.shift(12)-b/b.shift(12))*100
 relative_mom=rs3-rs3.shift(3)
 # Cycle labels based on relative 6M return and change in relative 3M return.
 # This is a market-relative classification, NOT an industry earnings cycle.
 for dt in both.index:
  v=rs6.loc[dt];m=relative_mom.loc[dt]
  stage=('Leading' if v>=0 and m>=0 else 'Weakening' if v>=0 else 'Improving' if m>=0 else 'Lagging') if pd.notna(v) and pd.notna(m) else 'Insufficient history'
  history.append({'date':str(dt.date()),'market':row.market,'sector':row.sector,'ticker':row.ticker,'stage':stage,'rs_6m':v,'rs_3m':rs3.loc[dt],'momentum_change':m,'relative_ratio':ratio.loc[dt]})
 last=both.index[-1];h=both[row.ticker]
 # Daily RSI calculated from daily observations; missing if insufficient.
 daily=wide[row.ticker].dropna();delta=daily.diff();up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean();down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean();rsi=(100-100/(1+up/down.replace(0,np.nan))).iloc[-1]
 outputs.append({'market':row.market,'sector':row.sector,'ticker':row.ticker,'benchmark':row.benchmark,'source_type':row.kind,'note':row.note,'asof':str(last.date()),'return_1m':(s/s.shift(1)-1).iloc[-1]*100,'return_3m':(s/s.shift(3)-1).iloc[-1]*100,'return_6m':(s/s.shift(6)-1).iloc[-1]*100,'return_12m':(s/s.shift(12)-1).iloc[-1]*100,'rs_1m':rs1.iloc[-1],'rs_3m':rs3.iloc[-1],'rs_6m':rs6.iloc[-1],'rs_12m':rs12.iloc[-1],'momentum_change':relative_mom.iloc[-1],'rsi':rsi,'stage':history[-1]['stage']})
if not outputs:raise SystemExit('Not enough matched sector and benchmark history')
pd.DataFrame(outputs).to_parquet(ROOT/'data/sector_snapshot.parquet',index=False)
pd.DataFrame(history).to_parquet(ROOT/'data/sector_history.parquet',index=False)
print('Computed',len(outputs),'sector comparisons')
