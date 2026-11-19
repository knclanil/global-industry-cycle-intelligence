"""Rebuild dashboard-ready India fundamentals from stored, verified snapshots.
Never fetches financial data or assumes an unavailable field is zero.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import pandas as pd
from india_financial_data import load_company, summary_row, aggregate_member_financials


def collect_snapshots(memberships: pd.DataFrame, company_directory: pd.DataFrame, data_dir: Path):
    """Rebuild missing summary from company JSONs; at most one file per NSE company."""
    if company_directory.empty or 'company_key' not in company_directory:
        return pd.DataFrame()
    results = []
    for _, company in company_directory.drop_duplicates('company_key').iterrows():
        key = str(company['company_key'])
        payload = load_company(key, root=data_dir)
        if payload is None:
            continue
        row = summary_row(payload)
        row['company_key'] = key
        results.append(row)
    return pd.DataFrame(results)


def build_groups(memberships: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    if memberships.empty or not {'company_key','category','index_name','index_slug'}.issubset(memberships):
        return pd.DataFrame()
    lookup = {str(row['company_key']):row.to_dict() for _,row in summary.iterrows()} if 'company_key' in summary else {}
    output=[]
    for slug, group in memberships.groupby('index_slug',dropna=True):
        row = group.iloc[0]
        output.append(aggregate_member_financials(group.to_dict('records'),lookup,'Index',
                str(row['index_name']),str(slug),str(row.get('parent_universe',''))))
    factors=memberships[memberships['category']=='Factor']
    if 'factor_family' in factors:
        for name, group in factors.groupby('factor_family',dropna=True):
            if not name: continue
            output.append(aggregate_member_financials(group.to_dict('records'),lookup,'Factor Family',str(name)))
    return pd.DataFrame(output)


def merge_session_research(summary: pd.DataFrame, companies: pd.DataFrame, session_results: dict) -> pd.DataFrame:
    """Expose already downloaded Screener fundamentals for selected companies.

    This is session-only, not persistent coverage, and retains source labels.
    Never invents a missing metric, price or filing period.
    """
    if companies.empty or not session_results:
        return summary
    by_symbol = {str(row.get('symbol','')).upper(): str(row.get('company_key',''))
                 for _,row in companies.iterrows()}
    df=summary.copy()
    records={str(row['company_key']):row.to_dict() for _,row in df.iterrows()} if 'company_key' in df else {}
    from india_valuation_reference import aligned_annual
    from india_valuation_reference import latest
    import math
    def finite(x):
        try:
            n=float(x)
            return n if math.isfinite(n) else None
        except (ValueError,TypeError):
            return None
    for symbol, packet in session_results.items():
        key=by_symbol.get(str(symbol).upper())
        if not key or not isinstance(packet,dict): continue
        tables=packet.get('screener',{}).get('tables',{})
        if not tables: continue
        metrics=packet.get('assessment',{}).get('metrics',{})
        record=records.get(key, {'company_key':key})
        originals=companies[companies['company_key']==key]
        for k in ('symbol','company_name','isin','industry'):
            record.setdefault(k, str(originals.iloc[0].get(k,'')))
        record['source_label']='Screener consolidated · session research'
        record['retrieved_utc']=packet.get('loaded_utc','')
        # Financial summary uses raw INR while Screener reports INR crore.
        for target,source in [('revenue','sales_cr'),('net_income','net_profit_cr'),
                              ('operating_cash_flow','cfo_cr')]:
            val=finite(metrics.get(source))
            if val is not None: record[target]=val*10_000_000
        v=finite(metrics.get('eps_inr'))
        if v is not None: record['diluted_eps']=v
        m=record.get('revenue')
        n=record.get('net_income')
        if finite(m) not in (None,0) and finite(n) is not None:
            record['net_margin']=float(n)/float(m)
        for k in ('revenue_yoy','operating_margin','roe','fcf_margin','pe'):
            if k not in record: record[k]=None
        val=finite(packet.get('selected',{}).get('trailing_pe'))
        if val is not None: record['pe']=val
        pl=tables.get('Profit & Loss')
        if pl is not None:
            sales=aligned_annual(pl,[r'^Sales\s*\+?$',r'^Revenue'])
            if len(sales): record['financial_period']=str(sales.index[-1])
        if record.get('financial_period'): record['income_period']=record['financial_period']
        records[key]=record
    return pd.DataFrame(list(records.values()))
