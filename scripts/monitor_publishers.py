"""Capture metadata from explicitly configured official RSS/Atom feeds; no full-text copying."""
import json,hashlib,datetime
from pathlib import Path
import feedparser
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data/publications.json'
existing=json.loads(P.read_text()) if P.exists() else []
seen={item['id'] for item in existing}
added=0
for pub in json.loads((ROOT/'config/publishers.json').read_text()):
 if not pub.get('feed'): continue
 try:
  parsed=feedparser.parse(pub['feed'])
  if parsed.bozo and not parsed.entries: raise RuntimeError(str(parsed.bozo_exception))
  for e in parsed.entries[:30]:
   link=e.get('link',''); title=e.get('title','').strip()
   if not link or not title: continue
   key=hashlib.sha256((pub['name']+'|'+link).encode()).hexdigest()[:20]
   if key in seen: continue
   existing.append({'id':key,'publisher':pub['name'],'market':pub['market'],'industry':pub['industry'],'title':title,'url':link,'published':e.get('published',e.get('updated','')),'discovered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'summary':'','assessment':'Not reviewed','source_type':'RSS metadata'})
   seen.add(key);added+=1
  print(pub['name'],'ok')
 except Exception as exc: print(pub['name'],'failed:',str(exc)[:180])
existing.sort(key=lambda x:x.get('discovered_utc',''),reverse=True)
P.write_text(json.dumps(existing[:2000],indent=2,ensure_ascii=False))
print('New publications:',added)
