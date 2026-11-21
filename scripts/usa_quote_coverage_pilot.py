#!/usr/bin/env python3
"""USA-only trial: enrich verified ETF issuers with dated USD Yahoo quotes.

Prioritizes issuers with cached fundamental data; never invents quote multiples.
Does not touch India or Knowledge Graph. Run in GitHub Actions, not Streamlit.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path
from tempfile import NamedTemporaryFile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
QUOTES = ROOT / 'data/usa_research/quotes.csv'
REPORT = ROOT / 'data/usa_research/quote_pilot_report.json'
FIELDS = ['ticker','price','market_cap','pe','pb','quote_asof','quote_source','currency']


def positive(value):
    try:
        number=float(value)
        return number if math.isfinite(number) and number>0 else None
    except (TypeError,ValueError):
        return None


def quote_recent(row, today=None, days=6):
    today=today or datetime.now(timezone.utc).date()
    try:
        stamp=date.fromisoformat(str(row.get('quote_asof',''))[:10])
    except (TypeError,ValueError):
        return False
    return (0 <= (today-stamp).days <= days and positive(row.get('price')) is not None
            and str(row.get('currency','')).upper()=='USD')


def quote_from_yahoo(ticker):
    import yfinance as yf
    t=yf.Ticker(ticker)
    history=t.history(period='7d',auto_adjust=False)
    if history.empty or 'Close' not in history:
        raise ValueError('Yahoo returned no recent price history')
    close=history['Close'].dropna()
    if close.empty:raise ValueError('Yahoo close series is empty')
    price=positive(close.iloc[-1])
    if price is None:raise ValueError('Invalid latest close')
    trade_date=pd.Timestamp(close.index[-1]).date()
    if (datetime.now(timezone.utc).date()-trade_date).days>7:
        raise ValueError('Latest quote price date too old')
    currency=''
    market_cap=pe=pb=None
    # Metadata failures do not discard a valid historical price.
    try:
        info=t.get_info() or {}
        returned=str(info.get('symbol') or '').upper().replace('.','-')
        if returned and returned != ticker.upper().replace('.','-'):
            raise ValueError(f'Ticker mismatch: requested {ticker}, received {returned}')
        currency=str(info.get('currency') or '').upper()
        market_cap=positive(info.get('marketCap'))
        pe=positive(info.get('trailingPE'))
        pb=positive(info.get('priceToBook'))
    except ValueError:
        raise
    except Exception:
        pass
    if not currency:
        try:currency=str(t.fast_info.get('currency') or '').upper()
        except Exception:pass
    if currency!='USD':
        raise ValueError('Currency not verified as USD; discarding quote')
    return {'ticker':ticker,'price':price,'market_cap':market_cap,'pe':pe,'pb':pb,
            'quote_asof':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            'quote_source':f'yahoo_finance_close_{trade_date.isoformat()}', 'currency':'USD'}


def select_targets(universe,existing,financial,requested=(),limit=25):
    universe=set(universe)
    requested=set(requested)
    if requested:
        invalid=requested-universe
        if invalid:raise ValueError('Not verified USA ETF tickers: '+', '.join(sorted(invalid)))
        candidates=sorted(requested)
    else:
        eligible=set()
        if isinstance(financial,pd.DataFrame) and {'ticker','fundamental_ready'}.issubset(financial.columns):
            eligible=set(financial.loc[financial.fundamental_ready.eq('Yes'),'ticker'].dropna().astype(str).str.upper())
        candidates=sorted(universe,key=lambda t:(t not in eligible,t))
    stale=[t for t in candidates if not quote_recent(existing.get(t,{}))]
    return stale[:limit] if limit else stale


def write_csv_atomic(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    df=pd.DataFrame(rows)
    for col in FIELDS:
        if col not in df:df[col]=None
    with NamedTemporaryFile('w',encoding='utf-8',newline='',dir=path.parent,delete=False) as f:
        df[FIELDS].sort_values('ticker').to_csv(f,index=False)
        temp=f.name
    os.replace(temp,path)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--limit',type=int,default=25)
    ap.add_argument('--tickers',default='')
    ap.add_argument('--pause',type=float,default=1.0)
    args=ap.parse_args()
    if args.limit<0:raise SystemExit('--limit must be >= 0')
    from usa_research_data import build_memberships,STORE
    source=STORE/'latest_holdings.parquet'
    if not source.exists():raise SystemExit(f'Missing verified USA holdings: {source}')
    memberships=build_memberships(pd.read_parquet(source))
    if memberships.empty:raise SystemExit('No verified USA memberships')
    universe=set(memberships.ticker.dropna().astype(str).str.upper().str.strip())
    existing={}
    if QUOTES.exists():
        for rec in pd.read_csv(QUOTES,dtype={'ticker':str}).to_dict('records'):
            ticker=str(rec.get('ticker','')).strip().upper()
            if ticker in universe:existing[ticker]=rec
    financial_path=ROOT/'data/usa_research/company_research.csv'
    financial=pd.read_csv(financial_path,low_memory=False) if financial_path.exists() else pd.DataFrame()
    requested={t.strip().upper() for t in args.tickers.split(',') if t.strip()}
    targets=select_targets(universe,existing,financial,requested,args.limit)
    result={'built_utc':datetime.now(timezone.utc).isoformat(),'verified_issuers':len(memberships),
            'verified_tickers':len(universe),'selected':len(targets),'fetched':0,'failed':0,'failures':{},
            'prices_before':sum(quote_recent(v) for v in existing.values())}
    for ticker in targets:
        try:
            row=quote_from_yahoo(ticker)
            old=existing.get(ticker,{})
            # Do not erase a valid existing multiple if new metadata fails; older
            # multiples MUST NOT be carried to a later quote as if newly dated.
            existing[ticker]=row
            result['fetched']+=1
        except Exception as exc:
            result['failed']+=1
            result['failures'][ticker]=str(exc)[:240]
        time.sleep(max(0,args.pause))
    if existing:write_csv_atomic(QUOTES,list(existing.values()))
    result['prices_after']=sum(quote_recent(v) for v in existing.values())
    result['valuations_after']=sum(quote_recent(v) and (positive(v.get('pe')) is not None or positive(v.get('pb')) is not None) for v in existing.values())
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    if targets and result['fetched']==0:raise SystemExit('All USA quote trial requests failed; check failure report, no India changes')

if __name__=='__main__':main()
