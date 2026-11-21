#!/usr/bin/env python3
"""Incremental SEC CompanyFacts and quote snapshots for verified USA ETF issuers.

Run in GitHub Actions, never from Streamlit. SEC requires SEC_USER_AGENT.
Do not infer ticker/CIK matches or use cross-country holdings.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / 'data' / 'fundamentals'
SEC_CACHE = ROOT / 'data' / 'sec_cache'
QUOTES = ROOT / 'data' / 'usa_research' / 'quotes.csv'
TICKER_URL = 'https://www.sec.gov/files/company_tickers.json'
FACT_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'

def utcnow(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False)
        temp=f.name
    os.replace(temp, path)

def atomic_csv(path, frame):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile('w', dir=path.parent, delete=False, newline='', encoding='utf-8') as f:
        frame.to_csv(f, index=False)
        temp=f.name
    os.replace(temp, path)

def age_days(path):
    return (datetime.now(timezone.utc)-datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)).days if path.exists() else None

def verified_tickers(path=None):
    from usa_research_data import build_memberships, STORE
    path=path or STORE/'latest_holdings.parquet'
    if not path.is_file(): raise RuntimeError('Verified USA holdings Parquet missing: '+str(path))
    members=build_memberships(pd.read_parquet(path))
    if members.empty: raise RuntimeError('No verified USA issuer memberships')
    return sorted({str(v).strip().upper() for v in members.ticker if str(v).strip()})

def sec_session():
    ua=os.environ.get('SEC_USER_AGENT','').strip()
    if not ua or '@' not in ua:
        raise RuntimeError('Set SEC_USER_AGENT in GitHub Actions Secrets to descriptive organization/name and contact email')
    s=requests.Session();s.headers.update({'User-Agent':ua,'Accept-Encoding':'gzip, deflate','Accept':'application/json'})
    return s

def get_json(session, url, attempts=3):
    last=None
    for attempt in range(attempts):
        try:
            resp=session.get(url, timeout=35)
            if resp.status_code in (429,500,502,503,504):
                last=f'HTTP {resp.status_code}'
                time.sleep(2**attempt*2);continue
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last=str(exc);time.sleep(2**attempt*2)
    raise RuntimeError(f'SEC fetch failed {url}: {last}')

def directory_entries(raw):
    if isinstance(raw,dict): raw=list(raw.values())
    if not isinstance(raw,list):raise ValueError('Unexpected SEC directory data')
    entries=[]
    for row in raw:
        try:
            ticker=str(row['ticker']).strip().upper().replace('.', '-')
            entries.append({'cik_str':int(row['cik_str']),'ticker':ticker,'title':str(row.get('title',''))})
        except (KeyError,ValueError,TypeError):continue
    return entries

def fetch_quote(ticker):
    import yfinance as yf
    t=yf.Ticker(ticker)
    info=t.get_info() or {}
    sym=str(info.get('symbol') or '').upper().replace('.', '-')
    if sym and sym!=ticker.replace('.', '-'):
        raise ValueError(f'Yahoo returned {sym}, expected {ticker}')
    fast=t.get_fast_info()
    def finite_positive(v):
        try:
            f=float(v)
            return f if 0<f<float('inf') else None
        except (TypeError,ValueError):return None
    def fast_value(k):
        try:return fast.get(k) if hasattr(fast,'get') else getattr(fast,k)
        except Exception:return None
    return dict(ticker=ticker,price=finite_positive(fast_value('last_price') or info.get('currentPrice')),
        market_cap=finite_positive(fast_value('market_cap') or info.get('marketCap')),
        pe=finite_positive(info.get('trailingPE')),pb=finite_positive(info.get('priceToBook')),
        quote_asof=utcnow(),quote_source='yahoo_finance_snapshot',
        currency=str(fast_value('currency') or info.get('currency') or '').upper())

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--limit',type=int,default=25,help='New/stale SEC requests; 0 means entire universe')
    p.add_argument('--tickers',default='',help='Comma-separated verified USA tickers')
    p.add_argument('--stale-days',type=int,default=28)
    p.add_argument('--quotes',action='store_true',help='Fetch and publish Yahoo quote metadata for selected/attempted issuers')
    p.add_argument('--quotes-limit',type=int,default=25)
    p.add_argument('--audit-only',action='store_true')
    p.add_argument('--pause',type=float,default=.25)
    args=p.parse_args()
    universe=verified_tickers()
    requested={x.strip().upper() for x in args.tickers.split(',') if x.strip()}
    invalid=requested-set(universe)
    if invalid:raise SystemExit('Requested symbols not in VERIFIED USA holdings: '+', '.join(sorted(invalid)))
    targets=sorted(requested) if requested else universe
    existing=pd.read_csv(QUOTES,dtype={'ticker':str}).to_dict('records') if QUOTES.is_file() else []
    quote_records={str(x.get('ticker','')).upper():x for x in existing}
    stats={'universe':len(universe),'selected':len(targets),'cached_before':0,'sec_fetched':0,
           'sec_failed':0,'quote_fetched':0,'quote_failed':0,'errors':{},'built_utc':utcnow()}
    retry_path=ROOT/'data'/'usa_research'/'sec_retry_state.json'
    try:retry_state=json.loads(retry_path.read_text()) if retry_path.exists() else {}
    except (OSError, ValueError):retry_state={}
    session=None
    directory_file=CACHE/'sec_company_directory.json'
    if not args.audit_only:
        # Reuse existing directory if fresh or for offline audit; otherwise refresh it.
        if not directory_file.exists() or (age_days(directory_file) or 0)>14:
            session=sec_session()
            entries=directory_entries(get_json(session,TICKER_URL))
            atomic_json(directory_file,entries)
            time.sleep(max(.1,args.pause))
    if not directory_file.exists():raise RuntimeError('No cached SEC directory; run collection with SEC_USER_AGENT')
    directory=directory_entries(json.loads(directory_file.read_text()))
    matches={}
    for row in directory:matches.setdefault(row['ticker'],[]).append(row)
    for ticker in targets:
        candidate=matches.get(ticker.replace('.','-'),[])
        if len(candidate)!=1:
            stats['errors'][ticker]='Missing/ambiguous SEC CIK match';continue
        cik=candidate[0]['cik_str']
        dest=CACHE/f'facts_{cik:010d}.json'
        fallback=SEC_CACHE/f'CIK{cik:010d}.json'
        cached=dest if dest.exists() else fallback
        if cached.exists():stats['cached_before']+=1
        should_fetch=not args.audit_only and (not cached.exists() or age_days(cached)>=max(0,args.stale_days))
        previous_failure=retry_state.get(ticker,{})
        try:
            failed_at=datetime.fromisoformat(str(previous_failure.get('last_failure','')))
            if failed_at.tzinfo is None: failed_at=failed_at.replace(tzinfo=timezone.utc)
            cooldown=failed_at>datetime.now(timezone.utc)-timedelta(hours=48)
        except (TypeError,ValueError):cooldown=False
        if should_fetch and not cooldown and (args.limit==0 or stats['sec_fetched']+stats['sec_failed']<args.limit):
            try:
                session=session or sec_session()
                raw=get_json(session,FACT_URL.format(cik=cik))
                if int(raw.get('cik',-1))!=cik or 'facts' not in raw:
                    raise ValueError('Companyfacts CIK or contents mismatch')
                atomic_json(dest,raw)
                stats['sec_fetched']+=1
                retry_state.pop(ticker,None)
            except Exception as exc:
                stats['sec_failed']+=1;stats['errors'][ticker]=f'SEC: {str(exc)[:150]}'
                retry_state[ticker]={'last_failure':utcnow(),'reason':str(exc)[:150]}
            time.sleep(max(.15,args.pause))
        # Quote requests are independent: do not lose SEC evidence on Yahoo failures.
        if args.quotes and not args.audit_only and stats['quote_fetched']+stats['quote_failed']<args.quotes_limit:
            previous=quote_records.get(ticker,{})
            date=str(previous.get('quote_asof') or '')[:10]
            try:age=(datetime.now(timezone.utc).date()-datetime.fromisoformat(date).date()).days
            except ValueError:age=9999
            if age >= 7:
                try:
                    quote_records[ticker]=fetch_quote(ticker);stats['quote_fetched']+=1
                except Exception as exc:
                    stats['quote_failed']+=1;stats['errors'][ticker]=f'Quote: {str(exc)[:150]}'
    if not args.audit_only:
        atomic_json(retry_path,retry_state)
    if args.quotes and not args.audit_only and quote_records:
        atomic_csv(QUOTES,pd.DataFrame(list(quote_records.values())).sort_values('ticker'))
    stats['sec_cached_after']=sum(any(p.exists() for p in (CACHE/f'facts_{r[0]["cik_str"]:010d}.json',SEC_CACHE/f'CIK{r[0]["cik_str"]:010d}.json')) for t in universe if len(r:=matches.get(t.replace('.','-'),[]))==1)
    path=ROOT/'data'/'usa_research'/'collection_report.json'
    atomic_json(path,stats)
    print(json.dumps(stats,indent=2))

if __name__=='__main__':main()
