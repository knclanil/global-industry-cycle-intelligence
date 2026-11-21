#!/usr/bin/env python3
"""Offline USA financial cache summarizer. No HTTP requests and no fabricated quotes.

Run after the existing SEC facts refresh. Writes a mergeable financial snapshot;
only already verified USA holding issuers are included. Safe on partial caches.
"""
from __future__ import annotations
import json
import sys
import math
from datetime import date, datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from usa_research_data import build_memberships
from usa_research_data import STORE, OUT, ROOT as DATA_ROOT


def num(table,label,period):
    if label not in table.index or period not in table.columns:return None
    x=pd.to_numeric(pd.Series([table.at[label,period]]),errors='coerce').iloc[0]
    return float(x) if pd.notna(x) else None


def div(a,b):return a/b if a is not None and b is not None and b!=0 else None


def financials_for(ticker):
    from sec_financials import load_company,statements,is_bank
    raw,cik,_=load_company(ticker)
    tables=statements(raw,'annual',6,ticker=ticker)
    inc,bal,cf=(tables[k][0] for k in ['Income Statement','Balance Sheet','Cash Flow'])
    common=set(inc.columns)&set(bal.columns)
    if not common:raise ValueError('No aligned income and balance reporting period')
    period=max(common)
    prev=sorted(inc.columns,reverse=True)
    rev=num(inc,'Revenue',period);net=num(inc,'Net income',period)
    old=num(inc,'Revenue',prev[prev.index(period)+1]) if period in prev and prev.index(period)+1<len(prev) else None
    equity=num(bal,'Stockholders equity',period)
    debt=num(bal,'Long-term debt',period)
    op=num(inc,'Operating income',period)
    ocf=num(cf,'Operating cash flow',period)
    fcf=num(cf,'Free cash flow',period)
    bank=is_bank(raw,ticker)
    roe=div(net,equity) if equity is not None and equity>0 else None
    # Long-term debt only; do not mislabel as total debt.
    dte=div(debt,equity) if equity is not None and equity>0 and not bank else None
    return dict(sec_cik=str(cik),financial_period=str(period),financial_source='SEC companyfacts / US GAAP',revenue=rev,net_income=net,
        revenue_yoy=div(rev-old,abs(old)) if rev is not None and old not in (None,0) else None,
        roe=roe,operating_margin=div(op,rev) if not bank else None,
        operating_cash_flow=ocf,free_cash_flow=fcf,debt_to_equity=dte,
        fundamental_ready='Yes' if net is not None and equity is not None and equity>0 and (rev is not None or bank) else 'No',
        valuation_ready='No',readiness_reason='No verified aligned market quote/peer valuation snapshot; ' +
          ('bank-specific assessment required' if bank else 'valuation not scored'),
        # Without dated prices/shares or comparable multiples, valuation cannot be computed.
        pe=None,pb=None,price=None,market_cap=None,
        quality_score=None,growth_score=None,valuation_score=None,research_score=None)


def finite(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def quote_snapshot(ticker, quote_by_ticker, max_age_days=7):
    """Accept only dated, USD, verified ticker quotes; don't invent valuation ratios."""
    row=quote_by_ticker.get(ticker.upper())
    if row is None: return {}
    try:
        age=(datetime.now(timezone.utc).date()-date.fromisoformat(str(row['quote_asof'])[:10])).days
    except (ValueError, TypeError, KeyError): return {}
    if not 0<=age<=max_age_days or str(row.get('currency','')).upper()!='USD':return {}
    return {k:finite(row.get(k)) for k in ('price','market_cap','pe','pb')} | {
        'quote_asof':str(row['quote_asof']),'quote_source':str(row.get('quote_source',''))}


def build():
    holdings=STORE/'latest_holdings.parquet'
    if not holdings.exists():raise SystemExit('Missing verified ETF holdings Parquet. Refresh iShares holdings first.')
    frame=build_memberships(pd.read_parquet(holdings))
    if frame.empty:raise SystemExit('No verified United States company memberships.')
    quote_path=ROOT/'data'/'usa_research'/'quotes.csv'
    quote_by_ticker={}
    if quote_path.is_file():
        q=pd.read_csv(quote_path,dtype={'ticker':str})
        if 'ticker' in q and not q['ticker'].duplicated().any():
            quote_by_ticker={str(r['ticker']).strip().upper():r for r in q.to_dict('records')}
    rows=[]
    for row in frame.itertuples(index=False):
        ticker=str(row.ticker).strip().upper()
        record=dict(company_key=row.company_key)
        # SEC directory matches strictly by ticker, and SEC facts must already be cached.
        try:record.update(financials_for(ticker))
        except (ValueError,RuntimeError,KeyError,OSError,TypeError) as exc:
            record.update(fundamental_ready='No',valuation_ready='No',
                          readiness_reason=f'Cached SEC facts unavailable: {str(exc)[:200]}')
        quote=quote_snapshot(ticker,quote_by_ticker)
        if quote:
            # Valuation multiples are obtained from dated Yahoo metadata, not
            # computed from mismatched fiscal/quote periods.
            record.update(quote)
            eligible=finite(quote.get('price')) is not None and (finite(quote.get('pe')) is not None or finite(quote.get('pb')) is not None)
            record['valuation_ready']='Yes' if eligible else 'No'
        # Freshness gate prevents stale SEC filings or quotes from looking investment-ready.
        try:
            age=(datetime.now(timezone.utc).date()-date.fromisoformat(str(record.get('financial_period',''))[:10])).days
        except (TypeError,ValueError):age=9999
        if not 0<=age<=540:
            record['fundamental_ready']='No'
            record['readiness_reason']='SEC financial period is stale or missing'
        if record.get('fundamental_ready')=='Yes' and record.get('valuation_ready')=='Yes':
            record['readiness_reason']='Comparable scores not calculated (peer/sector validation required)'
        rows.append(record)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT,index=False)
    usable=sum(r.get('fundamental_ready')=='Yes' for r in rows)
    report={'total_verified_usa_issuers':len(rows),'fundamental_ready':usable,
            'valuation_ready':sum(r.get('valuation_ready')=='Yes' for r in rows),'fully_scored':0,
            'method':'cached SEC company facts + dated optional Yahoo quote metadata + verified USA iShares memberships; no fabricated values or peer scores'}
    (OUT.parent/'build_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':build()
