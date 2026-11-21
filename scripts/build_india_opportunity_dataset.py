#!/usr/bin/env python3
"""Build auditable India company research universe from cached NSE + Yahoo records.

No online calls. Missing inputs remain missing. Industry-aware percentile scores
are computed only when readiness gates and adequate peers exist. Not advice.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
HOLDINGS = BASE / 'data' / 'india_holdings'
FIN = BASE / 'data' / 'india_financials'

METRICS = ('revenue', 'net_income', 'roe', 'operating_margin', 'revenue_yoy',
           'earnings_yoy', 'operating_cash_flow', 'free_cash_flow', 'debt_to_equity',
           'price', 'market_cap', 'pe', 'pb', 'ev_to_ebitda', 'fcf_yield')
FIELDS = ('company_key','company','ticker','isin','industry','sectors','factors',
          'source_indices','factor_count','sector_count','index_count','verified_memberships',
          'income_period','balance_period','cashflow_period','retrieved_utc','quote_asof',
          'statement_age_days','quote_age_days','financial_fresh','quote_fresh',
          'fundamental_ready','valuation_ready','research_ready',
          'quality_score','growth_score','valuation_score','research_score',
          'quality_metric_count','growth_metric_count','valuation_metric_count',
          'peer_group','peer_count','readiness_reason','coverage_flags') + METRICS
BANK_WORDS = ('BANK','BANKING','FINANCIAL SERVICES','FINANCE','INSURANCE','NBFC','LENDING')


def read_csv(path):
    if not Path(path).is_file():
        return []
    with open(path,encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        value=float(v)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def boolstr(value):
    return 'Yes' if value else 'No'


def age(value, today=None):
    if not value or str(value).strip() in ('','nan','None'):
        return None
    try:
        datepart=date.fromisoformat(str(value)[:10])
        return ((today or datetime.now(timezone.utc).date())-datepart).days
    except ValueError:
        return None


def distinct(vals):
    return sorted({str(x).strip() for x in vals if str(x).strip()},key=str.casefold)


def index_membership(companies, constituents):
    verified={c.get('company_key') for c in companies if c.get('company_key')}
    seen=set()
    out=defaultdict(lambda:{'sector':set(),'factor':set(),'indices':set(),'row_count':0})
    for r in constituents:
        key=r.get('company_key')
        if key not in verified or r.get('source_type') not in ('direct_nse',''):
            continue
        ident=(key, r.get('index_slug',''))
        if ident in seen: continue
        seen.add(ident)
        row=out[key]
        row['row_count']+=1
        if r.get('index_name'): row['indices'].add(r['index_name'].strip())
        if r.get('category')=='Factor' and r.get('factor_family'):
            row['factor'].add(r['factor_family'].strip())
        if r.get('category')=='Sector' and r.get('index_name'):
            row['sector'].add(r['index_name'].strip())
    return out


def percentile(value, others, higher=True, min_peers=5):
    """Cross-sectional rank against at least `min_peers` OTHER valid companies."""
    if value is None or len(others)<min_peers:
        return None
    lower=sum(x<value for x in others)
    tied=sum(x==value for x in others)
    p=100*(lower+0.5*tied)/len(others)
    return round(p if higher else 100-p,1)


def score_components(rows, min_peers=5):
    peers=defaultdict(list)
    for r in rows:
        peers[r['peer_group']].append(r)
    configuration={
        'quality':(('roe',True),('operating_margin',True),('debt_to_equity',False),('fcf_yield',True)),
        'growth':(('revenue_yoy',True),('earnings_yoy',True)),
        'valuation':(('pe',False),('pb',False),('ev_to_ebitda',False),('fcf_yield',True)),
    }
    for row in rows:
        is_fin=row['peer_group']=='Financials'
        group=peers[row['peer_group']]
        row['peer_count']=len(group)
        result={}
        for component,metrics in configuration.items():
            if component=='quality' and is_fin:
                metrics=(('roe',True),)  # nonfinancial leverage and margin incomparable
            if component=='valuation' and is_fin:
                metrics=(('pb',False),('pe',False))
            values=[]
            for metric,higher in metrics:
                x=row['_values'].get(metric)
                if x is None: continue
                if component=='valuation' and x<=0: continue
                if component=='quality' and metric=='fcf_yield' and is_fin: continue
                available=[r['_values'][metric] for r in group if r['company_key'] != row['company_key']
                           and r['_values'].get(metric) is not None
                           and (component!='valuation' or r['_values'][metric]>0)]
                p=percentile(x,available,higher,min_peers)
                if p is not None: values.append(p)
            min_metrics=1 if is_fin and component in ('quality','valuation') else (2 if component=='quality' else 1)
            row[f'{component}_metric_count']=len(values)
            result[component]=round(sum(values)/len(values),1) if len(values)>=min_metrics else None
            row[f'{component}_score']=result[component]
        # Avoid misleading 'total score' if one critical component is absent.
        row['research_score']=round(0.45*result['quality']+0.20*result['growth']+0.35*result['valuation'],1) if all(v is not None for v in result.values()) and row['research_ready']=='Yes' else None
        reasons=[]
        if row['fundamental_ready']=='No': reasons.append('missing fundamental KPIs')
        if row['valuation_ready']=='No': reasons.append('missing valuation KPIs')
        if row['financial_fresh']=='No': reasons.append('financial statements stale/unknown')
        if row['quote_fresh']=='No': reasons.append('quote stale/unknown')
        if row['peer_count'] < min_peers+1: reasons.append('insufficient comparable company peers')
        if any(v is None for v in result.values()): reasons.append('insufficient comparable scored metrics')
        row['readiness_reason']='; '.join(reasons) if reasons else 'Ready for comparative research (not investment advice)'
    return rows


def build(companies, constituents, finance, today=None, min_peers=5):
    today=today or datetime.now(timezone.utc).date()
    memberships=index_membership(companies,constituents)
    financial={r['company_key']:r for r in finance if r.get('company_key')}
    out=[]
    for company in companies:
        key=company.get('company_key')
        if not key: continue
        f=financial.get(key,{})
        m=memberships.get(key,{'sector':set(),'factor':set(),'indices':set(),'row_count':0})
        industry=company.get('industry','')
        finclass=any(w in industry.upper() for w in BANK_WORDS)
        group='Financials' if finclass else (industry.strip() or 'Unknown')
        vals={k:num(f.get(k)) for k in METRICS}
        fa=age(f.get('financial_period') or f.get('income_period'),today)
        qa=age(f.get('quote_asof'),today)
        financial_fresh=fa is not None and 0<=fa<=540
        quote_fresh=qa is not None and 0<=qa<=30
        fundamental=all(vals[k] is not None for k in ('revenue','net_income','roe'))
        valuation=fundamental and vals['price'] is not None and vals['price']>0 and any(vals[k] is not None and vals[k]>0 for k in ('pe','pb'))
        ready=fundamental and valuation and financial_fresh and quote_fresh
        row=dict(company_key=key, company=company.get('company_name',''),ticker=company.get('symbol',''),
                 isin=company.get('isin',''),industry=industry,sectors=' | '.join(distinct(m['sector'])),
                 factors=' | '.join(distinct(m['factor'])),source_indices=' | '.join(distinct(m['indices'])),
                 factor_count=len(m['factor']),sector_count=len(m['sector']),index_count=len(m['indices']),
                 verified_memberships=m['row_count'],income_period=f.get('income_period',''),
                 balance_period=f.get('balance_period',''),cashflow_period=f.get('cashflow_period',''),
                 retrieved_utc=f.get('retrieved_utc',''),quote_asof=f.get('quote_asof',''),
                 statement_age_days=fa,quote_age_days=qa,
                 financial_fresh=boolstr(financial_fresh),quote_fresh=boolstr(quote_fresh),
                 fundamental_ready=boolstr(fundamental),valuation_ready=boolstr(valuation),
                 research_ready=boolstr(ready),peer_group=group,
                 coverage_flags=' | '.join(k for k in METRICS if vals[k] is None),_values=vals)
        row.update(vals)
        out.append(row)
    score_components(out,min_peers=min_peers)
    out.sort(key=lambda r:(r['research_score'] is None,-(r['research_score'] or 0),r['ticker']))
    for r in out: r.pop('_values',None)
    return out


def write_atomic(path,data):
    from tempfile import NamedTemporaryFile
    import os
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile('w',encoding='utf-8',newline='',dir=path.parent,delete=False,prefix='.pending-') as f:
        if isinstance(data,list):
            w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');w.writeheader();w.writerows(data)
        else:json.dump(data,f,indent=2,allow_nan=False)
        name=f.name
    os.replace(name,path)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--holdings-dir',type=Path,default=HOLDINGS)
    p.add_argument('--financial-dir',type=Path,default=FIN)
    p.add_argument('--min-peers',type=int,default=5)
    a=p.parse_args()
    companies=read_csv(a.holdings_dir/'companies.csv')
    if not companies:raise SystemExit('ERROR: NSE companies.csv not found or empty; run NSE refresh first')
    membership=read_csv(a.holdings_dir/'constituents.csv')
    fin=read_csv(a.financial_dir/'company_financial_summary.csv')
    rows=build(companies,membership,fin,min_peers=max(3,a.min_peers))
    write_atomic(a.financial_dir/'opportunity_research.csv',rows)
    report={'generated_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            'companies':len(rows),'verified_membership_companies':sum(r['verified_memberships']>0 for r in rows),
            'fundamental_ready':sum(r['fundamental_ready']=='Yes' for r in rows),
            'valuation_ready':sum(r['valuation_ready']=='Yes' for r in rows),
            'research_ready':sum(r['research_ready']=='Yes' for r in rows),
            'research_scored':sum(r['research_score'] is not None for r in rows),
            'scoring_policy':'scores only if statements and quotes fresh; peer comparison min 5 other companies; Quality 45%, Growth 20%, Valuation 35%; no market positioning score without price-rotation integration',
            'limitations':'Research scores are exploratory within-industry comparisons, not investment advice; not historical backtested, no point-in-time survivorship adjustment; financial statement scope unverified; scores may be unavailable.'}
    write_atomic(a.financial_dir/'opportunity_build_report.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
