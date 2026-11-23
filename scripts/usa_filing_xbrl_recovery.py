#!/usr/bin/env python3
"""Incremental SEC 10-K inline-XBRL recovery. No third-party page scraping.

Only whitelisted standard concepts are admitted automatically. Custom extension
concepts require an explicit reviewed mapping in data/usa_research/xbrl_aliases.json.
Each recovered fact retains its filing accession and source URL in the cache.
"""
from __future__ import annotations
import argparse, json, os, re, time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('data/usa_research/filing_xbrl_cache')
TARGETS={'RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenueFromContractWithCustomerIncludingAssessedTax','SalesRevenueGoodsNet','SalesRevenueServicesNet','NetIncomeLoss','ProfitLoss','NetIncomeLossAvailableToCommonStockholdersBasic','OperatingIncomeLoss','AssetsCurrent','LiabilitiesCurrent','StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','CommonStockholdersEquity','EarningsPerShareDiluted','EarningsPerShareBasic','Assets','Liabilities','GrossProfit','OperatingExpenses','LiabilitiesNoncurrent'}
VALID_UNITS={'USD','USD/shares'}

def get(url,agent,timeout=35):
    if not agent or '@' not in agent: raise ValueError('SEC_USER_AGENT must include a contact email')
    req=Request(url,headers={'User-Agent':agent,'Accept-Encoding':'identity','Accept':'application/json,text/html,*/*'})
    with urlopen(req,timeout=timeout) as resp:
        data=resp.read(25_000_000+1)
        if len(data)>25_000_000: raise ValueError('SEC document exceeds size limit')
        return data

def local_name(tag):return str(tag.name or '').split(':')[-1].lower()

def parse_ixbrl(html,accession,url,aliases=None):
    """Return SEC CompanyFacts-compatible observations from an inline-XBRL 10-K."""
    aliases=aliases or {}
    soup=BeautifulSoup(html,'html.parser')
    contexts={}; units={}
    for t in soup.find_all(True):
        kind=local_name(t)
        if kind=='context' and t.get('id'):
            period=t.find(lambda x:local_name(x)=='period')
            if not period:continue
            def field(n):
                v=period.find(lambda x:local_name(x)==n)
                return v.get_text(strip=True) if v else None
            # Segment-specific facts must not be used as consolidated issuer KPIs.
            if t.find(lambda x:local_name(x) in ('segment','scenario')):continue
            start=field('startdate');end=field('enddate') or field('instant')
            if end:contexts[t['id']]=(start,end)
        elif kind=='unit' and t.get('id'):
            measures=[v.get_text(strip=True).split(':')[-1].lower() for v in t.find_all(lambda x:local_name(x)=='measure')]
            unit='USD/shares' if measures==['usd','shares'] else 'USD' if measures==['usd'] else None
            if unit:units[t['id']]=unit
    out={};rejected=0
    for t in soup.find_all(True):
        if local_name(t)!='nonfraction' or not t.get('name'):continue
        raw_name=t['name']; concept=raw_name.split(':')[-1]
        prefix=raw_name.split(':')[0].lower() if ':' in raw_name else ''
        approved=concept if prefix in ('us-gaap','us_gaap') and concept in TARGETS else aliases.get(raw_name)
        if approved not in TARGETS:
            rejected+=1;continue
        context=contexts.get(t.get('contextref',''));unit=units.get(t.get('unitref',''))
        if not context or unit not in VALID_UNITS:continue
        if unit=='USD/shares' and approved not in ('EarningsPerShareDiluted','EarningsPerShareBasic'):continue
        if unit=='USD' and approved in ('EarningsPerShareDiluted','EarningsPerShareBasic'):continue
        try:
            raw=t.get_text(' ',strip=True).replace(',','').replace('$','').replace(' ','')
            if raw in ('','-','—','–'):continue
            if raw.startswith('(') and raw.endswith(')'):raw='-'+raw[1:-1]
            val=float(raw)*10**int(t.get('scale','0'))
            if t.get('sign')=='-':val=-val
            if not (-1e20 < val < 1e20):continue
            start,end=context
            if start:
                days=(date.fromisoformat(end)-date.fromisoformat(start)).days
                if not 300<=days<=400:continue
            elif approved not in {'AssetsCurrent','LiabilitiesCurrent','StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','CommonStockholdersEquity','Assets','Liabilities','LiabilitiesNoncurrent'}:continue
            obs={'end':end,'val':val,'form':'10-K','accn':accession,'filed':end,'source_url':url,'original_concept':raw_name}
            if start:obs['start']=start
            out.setdefault(approved,{}).setdefault(unit,[]).append(obs)
        except (ValueError,OverflowError,TypeError):continue
    return out,rejected

def merge_into_companyfacts(facts,filing):
    """Prefer existing official CompanyFacts; add missing filing observations only."""
    data=json.loads(json.dumps(facts))
    gaap=data.setdefault('facts',{}).setdefault('us-gaap',{})
    for concept,units in filing.get('facts',{}).items():
        for unit,obs in units.items():
            target=gaap.setdefault(concept,{}).setdefault('units',{}).setdefault(unit,[])
            existing={(o.get('accn'),o.get('start'),o.get('end'),o.get('val')) for o in target}
            for item in obs:
                key=(item.get('accn'),item.get('start'),item.get('end'),item.get('val'))
                if key not in existing:target.append(item);existing.add(key)
    return data

def choose_filing(submissions):
    recent=submissions.get('filings',{}).get('recent',{})
    rows=[]
    for i,form in enumerate(recent.get('form',[])):
        if form not in ('10-K','10-K/A'):continue
        try:
            accession=recent['accessionNumber'][i];doc=recent['primaryDocument'][i]
            filed=recent['filingDate'][i]
            if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession):continue
            if not re.fullmatch(r'[\w.\-]+\.(?:htm|html)',doc,re.I):continue
            rows.append((filed,accession,doc))
        except (KeyError,IndexError):continue
    return max(rows) if rows else None

def run(root=ROOT,limit=125,pause=.25,agent=None,retry_days=14):
    import pandas as pd
    agent=agent or os.environ.get('SEC_USER_AGENT','')
    gap=root/'data/usa_research/fundamental_kpi_status.csv'
    if not gap.exists():raise FileNotFoundError('Run existing fundamental ranking builder first to generate KPI status')
    df=pd.read_csv(gap,dtype={'sec_cik':'string'})
    queue=df[(df['rank_status']=='Incomplete') & df['sec_cik'].notna()].copy()
    cache=root/CACHE;cache.mkdir(parents=True,exist_ok=True)
    aliases_path=root/'data/usa_research/xbrl_aliases.json'
    aliases=json.loads(aliases_path.read_text()) if aliases_path.exists() else {}
    report={'built_utc':datetime.now(timezone.utc).isoformat(),'eligible_queue':int(queue['sec_cik'].nunique()),'attempted':0,'recovered_filings':0,'new_facts':0,'skipped_cached':0,'errors':{},'note':'Recovery requires SEC filing access; custom tags require explicit review.'}
    for cik in dict.fromkeys(queue['sec_cik'].tolist()):
        try:cik=int(float(cik))
        except (ValueError,TypeError):continue
        dest=cache/f'{cik:010d}.json'
        if dest.exists():
            try:
                old=json.loads(dest.read_text())
                age=(datetime.now(timezone.utc)-datetime.fromisoformat(old['checked_utc'])).days
                if age<retry_days:report['skipped_cached']+=1;continue
            except (ValueError,KeyError,TypeError):pass
        if limit and report['attempted']>=limit:break
        report['attempted']+=1
        try:
            submissions=json.loads(get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',agent))
            filing=choose_filing(submissions)
            if not filing:raise ValueError('No recent 10-K primary HTML in submissions')
            filed,accession,doc=filing
            url=f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace("-","")}/{doc}'
            html=get(url,agent)
            facts,rejected=parse_ixbrl(html,accession,url,aliases)
            # Override the placeholder period filed date with actual SEC filing date.
            for units in facts.values():
                for obs in units.values():
                    for item in obs:item['filed']=filed
            payload={'cik':cik,'checked_utc':datetime.now(timezone.utc).isoformat(),'accession':accession,'filing_url':url,'facts':facts,'unmapped_ix_facts':rejected,'status':'ok' if facts else 'no_recognized_facts'}
            if facts:report['recovered_filings']+=1
            report['new_facts']+=sum(len(v) for units in facts.values() for v in units.values())
        except (HTTPError,URLError,OSError,ValueError,KeyError) as e:
            payload={'cik':cik,'checked_utc':datetime.now(timezone.utc).isoformat(),'facts':{},'status':'error','error':str(e)[:220]}
            report['errors'][str(cik)]=str(e)[:220]
        dest.write_text(json.dumps(payload,indent=2)+'\n')
        time.sleep(max(0,pause))
    (root/'data/usa_research/filing_xbrl_recovery_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--limit',type=int,default=125);p.add_argument('--pause',type=float,default=.25);p.add_argument('--retry-days',type=int,default=14)
    a=p.parse_args();run(a.root,a.limit,a.pause,retry_days=a.retry_days)
