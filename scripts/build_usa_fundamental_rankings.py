#!/usr/bin/env python3
"""Build auditable US fundamentals/ranks from existing SEC CompanyFacts + quote cache.

Network-free, repeatable, verified issuer universe; no website scraping.  Financial
periods are annual and filing-date gated; incompatible finance firms are unranked.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
FIELDS = ('roe', 'current_ratio', 'operating_margin', 'net_margin', 'eps_growth_pct')
TAGS = {
 'revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenueFromContractWithCustomerIncludingAssessedTax','SalesRevenueGoodsNet','SalesRevenueServicesNet','RevenueFromContractWithCustomerIncludingAssessedTax'),
 'net_income': ('NetIncomeLoss','ProfitLoss'),
 'operating_income': ('OperatingIncomeLoss',),
 'current_assets': ('AssetsCurrent',),
 'current_liabilities': ('LiabilitiesCurrent',),
 'equity': ('StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'),
 'eps_diluted': ('EarningsPerShareDiluted','EarningsPerShareBasic'),
 'assets': ('Assets',),
 'liabilities': ('Liabilities',),
 'cash': ('CashAndCashEquivalentsAtCarryingValue',),
 'gross_profit': ('GrossProfit',),
 'operating_cash_flow': ('NetCashProvidedByUsedInOperatingActivities',),
 'capex': ('PaymentsToAcquirePropertyPlantAndEquipment',),
}
UNITS = {'eps_diluted': 'USD/shares'}


def num(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError): return None


def _annual_observation(facts:dict, field:str, fiscal_year:int, asof:date):
    """Prefer 10-K FY statement corresponding to fiscal year; latest amended filing wins."""
    namespace=facts.get('facts',{}).get('us-gaap',{})
    unit=UNITS.get(field,'USD')
    candidates=[]
    for tag_priority, tag in enumerate(TAGS[field]):
        obs=namespace.get(tag,{}).get('units',{}).get(unit,[])
        for o in obs:
            if o.get('form') not in ('10-K','10-K/A'): continue
            # SEC 'fy' labels the filing's fiscal year, not necessarily the
            # observation year: comparative FY2024 facts can appear in FY2025 filings.
            # Prefer explicit CY#### frames, otherwise use the observation end date.
            frame=str(o.get('frame') or '')
            frame_year=int(frame[2:6]) if re.fullmatch(r'CY\d{4}',frame) else None
            try: observation_year=date.fromisoformat(o['end']).year
            except (ValueError,TypeError,KeyError): continue
            if frame_year is not None and frame_year!=fiscal_year: continue
            if frame_year is None and observation_year!=fiscal_year: continue
            try:
                filed=date.fromisoformat(o['filed']); end=date.fromisoformat(o['end'])
                if filed > asof: continue
                start=date.fromisoformat(o['start']) if 'start' in o else None
            except (ValueError,KeyError,TypeError): continue
            if field in ('revenue','net_income','operating_income','eps_diluted','operating_cash_flow','capex'):
                if start is None or not 300 <= (end-start).days <= 400: continue
            value=num(o.get('val'))
            if value is None: continue
            # Fiscal-year fact must not be absurdly distant from its labeled FY.
            if abs(end.year-fiscal_year)>1: continue
            # Concept precedence is more important than amendment recency:
            # never substitute basic EPS for available diluted EPS.
            candidates.append((-tag_priority, filed, end, value, tag, o.get('accn','')))
    if not candidates:return None
    _, filed, end, value, tag, accession=max(candidates,key=lambda t:(t[0],t[1],t[2]))
    return {'value':value,'period_end':end.isoformat(),'filed':filed.isoformat(),
            'concept':tag,'accession':accession,'source':'SEC CompanyFacts'}


def annual_fields(facts:dict, asof:date|None=None, max_age_days=540):
    asof=asof or datetime.now(timezone.utc).date()
    years=range(asof.year,asof.year-5,-1)
    results={}
    for fy in years:
        n={name:_annual_observation(facts,name,fy,asof) for name in TAGS}
        # Must have income and balance data, aligned to ~same financial year.
        has_financials=any(n[f] for f in ('revenue','net_income','equity'))
        if not has_financials:continue
        ends=[date.fromisoformat(x['period_end']) for x in n.values() if x]
        if not ends or (asof-max(ends)).days > max_age_days:continue
        # Do not combine FY2018 balance sheet with FY2025 income.
        primary=[n.get('revenue'),n.get('net_income'),n.get('equity')]
        anchors=[date.fromisoformat(x['period_end']) for x in primary if x]
        if anchors and (max(anchors)-min(anchors)).days>45:continue
        # Never combine fields from different fiscal period ends; missing stays missing.
        anchor = max(anchors) if anchors else max(ends)
        n={key:(rec if rec and abs((date.fromisoformat(rec['period_end'])-anchor).days)<=45 else None)
           for key,rec in n.items()}
        # Select the most recent valid annual period, not a stale partial mixture.
        results=n;break
    if not results:return {}, {}
    vals={k:(v['value'] if v else None) for k,v in results.items()}
    def ratio(a,b):
        return a/b if a is not None and b is not None and b>0 else None
    rev=vals.get('revenue'); net=vals.get('net_income')
    # Do not compute margins for nonpositive revenue or ROE for nonpositive equity.
    metrics={
       'roe':100*ratio(net,vals.get('equity')) if ratio(net,vals.get('equity')) is not None else None,
       'current_ratio':ratio(vals.get('current_assets'),vals.get('current_liabilities')),
       'operating_margin':100*ratio(vals.get('operating_income'),rev) if ratio(vals.get('operating_income'),rev) is not None else None,
       'net_margin':100*ratio(net,rev) if ratio(net,rev) is not None else None,
       'eps_growth_pct':None,
       'eps_diluted':vals.get('eps_diluted'),
       'revenue':rev,'net_income':net,
       'gross_profit':vals.get('gross_profit'),
       'assets':vals.get('assets'),'liabilities':vals.get('liabilities'),
       'cash':vals.get('cash'),'operating_cash_flow':vals.get('operating_cash_flow'),
       'capital_expenditure':vals.get('capex'),
       'free_cash_flow':(vals['operating_cash_flow']-vals['capex'] if vals.get('operating_cash_flow') is not None and vals.get('capex') is not None else None),
    }
    ep=results.get('eps_diluted')
    if ep:
        prev_fy=date.fromisoformat(ep['period_end']).year-1
        prev=_annual_observation(facts,'eps_diluted',prev_fy,asof)
        if prev and prev['value'] != 0 and prev['concept']==ep['concept']:
            # Absolute prior EPS denominator preserves meaningful turnaround
            # direction for loss-making issuers; zero base is undefined.
            metrics['eps_growth_pct'] = 100*(ep['value']-prev['value'])/abs(prev['value'])
            results['eps_diluted_previous']=prev
    # Report most recent material reporting period; individual field periods remain in evidence.
    relevant=[x['period_end'] for x in results.values() if x]
    metrics['financial_period']=max(relevant) if relevant else None
    return metrics, results


def reference_links(ticker):
    t=quote(str(ticker).upper(),safe='.-')
    return {
      'stockanalysis_income_url':f'https://stockanalysis.com/stocks/{t}/financials/income-statement/',
      'stockanalysis_balance_url':f'https://stockanalysis.com/stocks/{t}/financials/balance-sheet/',
      'stockanalysis_cashflow_url':f'https://stockanalysis.com/stocks/{t}/financials/cash-flow-statement/',
      'stockanalysis_ratios_url':f'https://stockanalysis.com/stocks/{t}/financials/ratios/',
      'stockanalysis_metrics_url':f'https://stockanalysis.com/stocks/{t}/financials/metrics/',
      'finviz_url':f'https://finviz.com/stock?t={t}&p=d',
      'yahoo_income_url':f'https://finance.yahoo.com/quote/{t}/financials/',
      'yahoo_balance_url':f'https://finance.yahoo.com/quote/{t}/balance-sheet/',
      'yahoo_cashflow_url':f'https://finance.yahoo.com/quote/{t}/cash-flow/',
      'yahoo_statistics_url':f'https://finance.yahoo.com/quote/{t}/key-statistics/',
    }


def rank_frame(df:pd.DataFrame, *, group_by=None, exclude_financials=True):
    """Dense rank every metric high-is-good, then lexicographic total+cap tiebreak.

    Financial institutions are excluded because liquidity and margins are not
    comparable to those of general operating businesses.  A missing cap leaves
    a primary-score tie unresolved, rather than inventing a market-cap rank.
    """
    out=df.copy()
    for f in (*FIELDS,'market_cap'):out[f]=pd.to_numeric(out[f],errors='coerce')
    eligible=out[list(FIELDS)].notna().all(axis=1)
    if exclude_financials and 'industry' in out:
        financial=out['industry'].fillna('').str.contains(r'bank|insurance|financial|reit|credit|capital market|asset management',case=False,regex=True)
        eligible &= ~financial
    if exclude_financials and 'sectors' in out:
        sector_fin=out['sectors'].fillna('').str.contains('Financial',case=False,regex=False)
        eligible &= ~sector_fin
    out['ranking_eligible']=eligible
    out['ranking_reason']='Incomplete required SEC metrics'
    out.loc[eligible,'ranking_reason']='Ranked'
    out['total_fundamental_rank']=pd.NA
    out['market_cap_rank']=pd.NA
    out['final_rank']=pd.NA
    for f in FIELDS:out[f+'_rank']=pd.NA
    # Within optional comparable industry groups. Default whole eligible universe.
    groups=out.loc[eligible].groupby(group_by,dropna=False).groups.values() if group_by else [out.index[eligible]]
    for ids in groups:
        ids=list(ids)
        for f in FIELDS:
            out.loc[ids,f+'_rank']=out.loc[ids,f].rank(ascending=False,method='min').astype(int)
        out.loc[ids,'total_fundamental_rank']=out.loc[ids,[f+'_rank' for f in FIELDS]].astype(float).sum(axis=1).astype(int)
        # Market-cap rank exists ONLY for companies tied on the primary five-rank sum.
        # It is never added to or used to modify the total fundamental score.
        totals=out.loc[ids,'total_fundamental_rank']
        for total, tied in totals.groupby(totals).groups.items():
            tied=list(tied)
            if len(tied)>1:
                caps=out.loc[tied,'market_cap']
                out.loc[tied,'market_cap_rank']=caps.rank(ascending=False,method='min').astype('Int64')
        # Sort by total, cap only within ties, final key for deterministic display.
        subset=out.loc[ids].copy()
        subset['_c']=subset['market_cap'].fillna(float('-inf'))
        subset=subset.sort_values(['total_fundamental_rank','_c','ticker'],ascending=[True,False,True],kind='stable')
        # Simpler competition ranking via comparison tuple and ordered position.
        prev=None;winner_rank=0
        for position,(ix,row) in enumerate(subset.iterrows(),1):
            key=(row['total_fundamental_rank'],num(row['market_cap']))
            if key!=prev:winner_rank=position
            out.at[ix,'final_rank']=winner_rank
            prev=key
    if exclude_financials:
        excluded=~eligible & df[list(FIELDS)].notna().all(axis=1)
        out.loc[excluded,'ranking_reason']='Financial institution: metrics not comparable'
    return out


def build(root:Path=ROOT, asof:date|None=None):
    from usa_research_data import build_memberships
    from usa_sec_cache_reader import ticker_directory,cached_companyfacts
    holdings=root/'data/holdings/latest_holdings.parquet'
    if not holdings.exists():raise RuntimeError('Verified USA holdings missing; run existing holdings refresh')
    members=build_memberships(pd.read_parquet(holdings))
    if members.empty:raise RuntimeError('No verified USA memberships')
    directory=ticker_directory(root)
    quotes={}
    qp=root/'data/usa_research/quotes.csv'
    if qp.exists():
        q=pd.read_csv(qp)
        if 'ticker' in q:
            for row in q.to_dict('records'):
                symbol=str(row.get('ticker','')).strip().upper()
                if symbol and symbol not in quotes:quotes[symbol]=row
    rows=[];evidence=[];failures=[];urls=[]
    for m in members.to_dict('records'):
        ticker=str(m.get('ticker','')).strip().upper()
        row={k:m.get(k) for k in ('company_key','company','ticker','sectors','factors','industry')}
        row.update({f:None for f in (*FIELDS,'market_cap','revenue','net_income','eps_diluted','gross_profit','assets','liabilities','cash','operating_cash_flow','capital_expenditure','free_cash_flow')})
        row.update(financial_period=None,sec_cik=None)
        if ticker and ticker in directory:
            try:
                facts,cik=cached_companyfacts(root,ticker,directory)
                financial,fields=annual_fields(facts,asof)
                row.update(financial);row['sec_cik']=cik
                for field,rec in fields.items():
                    if rec:evidence.append(dict(company_key=m['company_key'],ticker=ticker,field=field,**rec))
            except (ValueError,TypeError,KeyError,OSError) as e:failures.append({'ticker':ticker,'reason':str(e)[:150]})
        else:failures.append({'ticker':ticker,'reason':'Not uniquely mapped to SEC CIK'})
        q=quotes.get(ticker,{})
        cap=num(q.get('market_cap'))
        # Market-cap tiebreak comes from existing separately sourced, dated quote cache.
        if cap is not None and cap>0 and str(q.get('currency','')).upper()=='USD':
            try:
                age=((asof or date.today())-date.fromisoformat(str(q.get('quote_asof',''))[:10])).days
            except (ValueError,TypeError):age=9999
            if 0<=age<=45:
                row['market_cap']=cap
                evidence.append(dict(company_key=m['company_key'],ticker=ticker,field='market_cap',value=cap,source=str(q.get('quote_source','quote cache')),period_end=str(q.get('quote_asof',''))[:10],filed=str(q.get('quote_asof',''))[:10],concept='market_cap',accession=''))
        rows.append(row)
        urls.append(dict(company_key=m['company_key'],ticker=ticker,**reference_links(ticker)))
    d=rank_frame(pd.DataFrame(rows))
    d['missing_kpis']=d.apply(lambda r: ','.join(f for f in FIELDS if pd.isna(r[f])),axis=1)
    d['rank_status']=d['ranking_eligible'].map({True:'Complete',False:'Incomplete'})
    d.loc[d['ranking_reason'].eq('Financial institution: metrics not comparable'),'rank_status']='Ineligible'
    out=root/'data/usa_research';out.mkdir(parents=True,exist_ok=True)
    d.to_csv(out/'fundamental_rankings.csv',index=False)
    audit=d[['company_key','ticker','ranking_eligible','ranking_reason',*FIELDS]].copy()
    for f in FIELDS:
        audit['missing_'+f]=audit[f].isna()
    audit['missing_metric_count']=audit[['missing_'+f for f in FIELDS]].sum(axis=1)
    audit['stockanalysis_url']=audit['ticker'].map(lambda t: reference_links(t)['stockanalysis_ratios_url'])
    audit['finviz_url']=audit['ticker'].map(lambda t: reference_links(t)['finviz_url'])
    audit.to_csv(out/'fundamental_kpi_gap_audit.csv',index=False)
    pd.DataFrame(evidence,columns=['company_key','ticker','field','value','source','period_end','filed','concept','accession']).to_csv(out/'fundamental_field_evidence.csv',index=False)
    pd.DataFrame(urls).to_csv(out/'financial_source_links.csv',index=False)
    gaps=d[['company_key','ticker','rank_status','ranking_reason','missing_kpis','sec_cik','financial_period']].copy()
    gaps.to_csv(out/'fundamental_kpi_gap_audit.csv',index=False)
    report={'built_utc':datetime.now(timezone.utc).isoformat(),'verified_companies':len(d),
            'ranked':int(d['ranking_eligible'].sum()),'unranked':int((~d['ranking_eligible']).sum()),
            'metric_coverage':{f:int(d[f].notna().sum()) for f in (*FIELDS,'market_cap')},
            'status_counts':{str(k):int(v) for k,v in d['rank_status'].value_counts().items()},
            'missing_metric_counts':{f:int(d[f].isna().sum()) for f in FIELDS},
            'gap_count_by_metric':{f:int(d[f].isna().sum()) for f in FIELDS},
            'sec_mapping_failures':len(failures),'sample_failures':failures[:30],
            'method':'5 SEC annual metric ranks (lower sum better); USD market cap used solely on ties; no web-page scraping',
            'limitations':'Financial sector excluded; annual-only; verified records with missing metrics remain unranked; source links for manual verification'}
    (out/'fundamental_ranking_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return d

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT)
    args=p.parse_args();build(args.root)
