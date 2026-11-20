"""Offline materialized views for the regional Streamlit workspaces.

Read only verified repository snapshots. Never fetch market or financial data from
Streamlit. Build outputs are atomic and preserve missing values as unknown.
Usage: python scripts/build_dashboard_cache.py [--include-sec]
"""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / 'data' / 'dashboard_cache'


def read_csv(path):
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False) if path.is_file() else pd.DataFrame()
    except (ValueError, OSError, pd.errors.ParserError):
        return pd.DataFrame()


def atomic_csv(frame: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='', suffix='.tmp', prefix='.building_', dir=path.parent, delete=False) as handle:
        tmp = Path(handle.name)
        frame.to_csv(handle, index=False)
    os.replace(tmp, path)


def atomic_json(value, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.tmp', prefix='.building_', dir=path.parent, delete=False) as handle:
        tmp = Path(handle.name)
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
    os.replace(tmp, path)


def _coalesce(value, fallback=''):
    return fallback if pd.isna(value) or str(value).strip().lower() in ('nan', 'none') else str(value).strip()


def build_india():
    source = read_csv(ROOT/'data/india_holdings/constituents.csv')
    fin = read_csv(ROOT/'data/india_financials/company_financial_summary.csv')
    columns = ['company_key','symbol','company_name','industry','isin','sector_indices','factor_indices','factor_families','index_memberships','financial_status','revenue','net_income','roe','operating_margin','net_margin','pe','financial_asof']
    if source.empty or not {'company_key','index_slug','category'}.issubset(source):
        return pd.DataFrame(columns=columns), pd.DataFrame(columns=['index_slug','index_name','category','factor_family','constituents','snapshot_utc']),pd.DataFrame()
    source=source.drop_duplicates(['company_key','index_slug']).copy()
    company=[]
    for key, g in source.groupby('company_key',sort=True):
        first=g.iloc[0]
        sg=g[g['category'].eq('Sector') | g['category'].eq('Thematic')]
        # All other named strategy indices retain their explicit source category.
        fg=g[g['category'].eq('Factor') | g['category'].eq('Strategy')]
        company.append(dict(company_key=key,symbol=_coalesce(first.get('symbol')),company_name=_coalesce(first.get('company_name')),
            industry=_coalesce(first.get('industry')),isin=_coalesce(first.get('isin')),
            sector_indices=' | '.join(sorted(sg.index_name.unique())) if 'index_name' in sg else '',
            factor_indices=' | '.join(sorted(fg.index_name.unique())) if 'index_name' in fg else '',
            factor_families=' | '.join(sorted(x for x in fg.factor_family.unique() if _coalesce(x))) if 'factor_family' in fg else '',
            index_memberships=g.index_slug.nunique(),financial_status='Not collected', revenue=None,net_income=None,roe=None,
            operating_margin=None,net_margin=None,pe=None,financial_asof=''))
    directory=pd.DataFrame(company)
    if not fin.empty and 'company_key' in fin:
        metrics=['company_key','revenue','net_income','roe','operating_margin','net_margin','pe','financial_period']
        available=[x for x in metrics if x in fin]
        filtered=fin[available].drop_duplicates('company_key')
        directory=directory.drop(columns=[c for c in metrics if c in directory and c!='company_key'],errors='ignore').merge(filtered,on='company_key',how='left')
        directory=directory.rename(columns={'financial_period':'financial_asof'})
        directory['financial_status']=directory['revenue'].where(directory['revenue'].ne(''),'')
        directory['financial_status']=directory['financial_status'].apply(lambda v:'Available' if _coalesce(v) else 'Not available')
    idx=source.groupby(['index_slug','index_name','category','factor_family'],dropna=False).agg(
        constituents=('company_key','nunique'),snapshot_utc=('snapshot_utc','max')).reset_index()
    # Direct join across distinct securities, not row counts, to avoid overlap inflation.
    sectors=source[source.category.isin(['Sector','Thematic'])].copy()
    factors=source[source.category.isin(['Factor','Strategy'])].copy()
    if sectors.empty or factors.empty: matrix=pd.DataFrame(columns=['sector_index','factor_family','companies'])
    else:
        pairs=sectors[['company_key','index_name']].merge(factors[['company_key','factor_family']],on='company_key').drop_duplicates()
        matrix=pairs.groupby(['index_name','factor_family']).company_key.nunique().rename('companies').reset_index().rename(columns={'index_name':'sector_index'})
    return directory,idx,matrix


def build_ishares(region):
    columns=['company_key','symbol','company_name','industry','country','isin','sector_indices','factor_indices','factor_families','index_memberships','avg_etf_weight_pct','financial_status']
    index_columns=['index_slug','index_name','category','factor_family','constituents','snapshot_utc']
    try:
        holdings=pd.read_parquet(ROOT/'data/holdings/latest_holdings.parquet')
    except FileNotFoundError:
        return pd.DataFrame(columns=columns),pd.DataFrame(columns=index_columns),pd.DataFrame()
    except (ImportError, OSError, ValueError) as exc:
        raise RuntimeError(f'Cannot read iShares parquet for {region}: {exc}. Do not publish empty materialized views.') from exc
    if holdings.empty or 'group' not in holdings:return pd.DataFrame(columns=columns),pd.DataFrame(columns=index_columns),pd.DataFrame()
    holdings=holdings[holdings.group.astype(str).str.startswith('Global' if region=='Global' else 'USA')].copy()
    if holdings.empty:return pd.DataFrame(columns=columns),pd.DataFrame(columns=index_columns),pd.DataFrame()
    holdings=holdings.drop_duplicates(['issuer_id','portfolio_id'])
    membership=[]
    for ident,g in holdings.groupby('issuer_id',sort=True):
        first=g.iloc[0]
        sector=g[g.group.astype(str).str.contains('Sector')]
        factor=g[g.group.astype(str).str.contains('Factor')]
        weights=pd.to_numeric(g.weight,errors='coerce') if 'weight' in g else pd.Series(dtype=float)
        membership.append(dict(company_key=ident,symbol=_coalesce(first.get('ticker')),company_name=_coalesce(first.get('company')),
            industry=_coalesce(first.get('sector')),country=_coalesce(first.get('country')),isin=_coalesce(first.get('isin')),
            sector_indices=' | '.join(sorted(set(sector.fund_title.dropna()))) if 'fund_title' in sector else '',
            factor_indices=' | '.join(sorted(set(factor.fund_title.dropna()))) if 'fund_title' in factor else '',
            factor_families='',index_memberships=g.portfolio_id.nunique(),
            avg_etf_weight_pct=round(float(weights.mean()),4) if weights.notna().any() else None,financial_status='Not matched'))
    company=pd.DataFrame(membership)
    idx=holdings.groupby(['portfolio_id','fund_title','group'],dropna=False).agg(constituents=('issuer_id','nunique'),snapshot_utc=('as_of','max')).reset_index()
    idx=idx.rename(columns={'portfolio_id':'index_slug','fund_title':'index_name','group':'category'})
    idx['factor_family']=''
    idx=idx[index_columns]
    return company,idx,pd.DataFrame()


def index_financials(region, companies, indices):
    """Aggregate only observed company metrics; no exposure-weight inference."""
    fields=['revenue','net_income','roe','operating_margin','net_margin','pe']
    out=[]
    for row in indices.to_dict('records'):
        name=str(row.get('index_name',''))
        # Membership delimiters are preserved in canonical materialized views.
        sector=companies.get('sector_indices',pd.Series(dtype=str)).fillna('').astype(str)
        factor=companies.get('factor_indices',pd.Series(dtype=str)).fillna('').astype(str)
        if not sector.empty:
            mask=sector.apply(lambda v:name in v.split(' | ')) | factor.apply(lambda v:name in v.split(' | '))
            g=companies.loc[mask]
        else:
            g=pd.DataFrame()
        entry={'index_name':name,'category':row.get('category',''),
               'constituents':int(row.get('constituents',0)),'financial_records':0}
        for field in fields:
            values=pd.to_numeric(g[field],errors='coerce') if field in g else pd.Series(dtype=float)
            entry[f'{field}_observations']=int(values.notna().sum())
            entry[f'median_{field}']=float(values.median()) if values.notna().any() else None
            if field=='revenue':entry['financial_records']=int(values.notna().sum())
        out.append(entry)
    return pd.DataFrame(out)


def build(include_sec=False):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    manifest={'built_utc':datetime.now(timezone.utc).isoformat(),'schema_version':1,'regions':{},'notes':[
        'ETF daily market prices are cached separately from their lower-frequency constituent snapshots.',
        'Missing or inaccessible observations are not replaced with zero.',
        'India values reflect only verified downloaded company snapshots; reference ratio snapshots do not establish annual statement history.',
        'USA and Global issuer identities remain region-separated. Global non-SEC issuers need independent financial coverage.']}
    for region in ('Global','USA','India'):
        if region=='India':company,idx,matrix=build_india()
        else:company,idx,matrix=build_ishares(region)
        slug=region.lower()
        atomic_csv(company, OUTPUT/f'{slug}_companies.csv')
        atomic_csv(idx, OUTPUT/f'{slug}_indices.csv')
        atomic_csv(matrix, OUTPUT/f'{slug}_sector_factor_matrix.csv')
        atomic_csv(index_financials(region,company,idx),OUTPUT/f'{slug}_index_financial_summary.csv')
        manifest['regions'][region]={'companies':int(len(company)),'source_indices':int(len(idx)),
            'index_memberships':int(pd.to_numeric(company.get('index_memberships',pd.Series(dtype=float)),errors='coerce').sum()),
            'financial_snapshots':int(company.financial_status.eq('Available').sum()) if 'financial_status' in company else 0,
            'source': 'NSE constituent snapshots' if region=='India' else 'Verified iShares ETF holdings'}
    # SEC ranking engine is CPU and IO heavy and not run in interactive UI.
    # Optional materialization from authoritative cached Company Facts, never from network.
    if include_sec:
        try:
            from fundamental_rankings_engine import get_rankings
            for region in ('USA','Global','India'):
                frame=get_rankings(region)
                if not frame.empty:
                    frame=frame.drop(columns=['History'],errors='ignore')
                    atomic_csv(frame,OUTPUT/f'{region.lower()}_fundamental_quality.csv')
                    manifest['regions'][region]['fundamental_profiles']=len(frame)
        except Exception as exc:
            manifest['fundamental_error']=f'{type(exc).__name__}: {str(exc)[:250]}'
    atomic_json(manifest, OUTPUT/'manifest.json')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--include-sec',action='store_true');a=p.parse_args()
    print(json.dumps(build(a.include_sec),indent=2))
