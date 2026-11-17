"""Collect published NSE index performance snapshot when NSE permits access.
No scraping bypass. Failure is recorded, never replaced by invented prices.
The configured index list is a watchlist, not a verified live NSE page export.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, csv, sys
import requests
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/nse_index_snapshot.json'
STATUS=ROOT/'data/nse_collection_status.json'
url='https://www.nseindia.com/api/allIndices'
headers={'User-Agent':'Mozilla/5.0 (compatible; ResearchDashboard/1.0)','Accept':'application/json','Referer':'https://www.nseindia.com/market-data/index-performances'}
watch={r['index_name'].strip().upper() for r in csv.DictReader((ROOT/'config/nse_indices.csv').open())}
status={'checked_utc':datetime.now(timezone.utc).isoformat(),'source':url,'status':'unavailable','count':0}
try:
 with requests.Session() as session:
  session.headers.update(headers)
  session.get('https://www.nseindia.com/',timeout=15)
  response=session.get(url,timeout=25)
  response.raise_for_status()
  payload=response.json()
 rows=payload.get('data',[])
 if not isinstance(rows,list): raise ValueError('Unexpected NSE response structure')
 normalized=[]
 for item in rows:
  name=str(item.get('index') or item.get('indexSymbol') or '').strip()
  if name.upper() not in watch: continue
  normalized.append({'index':name,'last':item.get('last'),'percent_change':item.get('percentChange'),'previous_close':item.get('previousClose'),'open':item.get('open'),'high':item.get('high'),'low':item.get('low'),'year_high':item.get('yearHigh'),'year_low':item.get('yearLow'),'reported_time':item.get('timeVal') or item.get('timestamp')})
 if not normalized:raise ValueError('No configured NSE indices found in response; check names/schema')
 OUT.write_text(json.dumps({'source':url,'retrieved_utc':status['checked_utc'],'rows':normalized},indent=2))
 status.update(status='ok',count=len(normalized))
 print('Saved NSE index snapshot:',len(normalized))
except Exception as exc:
 status['error']=str(exc)[:400]
 print('NSE snapshot unavailable:',status['error'])
STATUS.write_text(json.dumps(status,indent=2))
# Optional source: do not fail all other markets when NSE blocks automated access.
