"""USA opportunity research from verified iShares holdings and cached SEC facts.

Read-only at Streamlit render time. Never mix Global ETF membership with USA,
never infer fundamental strength from ETF membership, never invent quotes.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'data' / 'holdings'
OUT = ROOT / 'data' / 'usa_research' / 'company_research.csv'
FACTS_DIR = ROOT / 'data' / 'fundamentals'
SEC_DIR = ROOT / 'data' / 'sec_cache'
NUMBERS = ['membership_count','sector_count','factor_count','avg_weight','revenue','net_income',
           'revenue_yoy','roe','operating_margin','operating_cash_flow','free_cash_flow',
           'debt_to_equity','pe','pb','price','market_cap','quality_score','growth_score',
           'valuation_score','research_score']


def items(value):
    if value is None or pd.isna(value): return set()
    return {v.strip() for v in str(value).split('|') if v.strip()}


def match(value, chosen, mode='ANY'):
    if not chosen: return True
    seen=items(value)
    return set(chosen).issubset(seen) if mode == 'ALL' else bool(seen & set(chosen))


def filter_companies(df, sectors=(), factors=(), funds=(), mode='ANY', query='',
                     fundamental=False, valuation=False, scored=False):
    out=df.copy()
    for field, chosen in [('sectors',sectors),('factors',factors),('funds',funds)]:
        if chosen: out=out[out[field].map(lambda s:match(s,chosen,mode))]
    if query:
        mask=(out['company'].astype(str).str.contains(query,case=False,regex=False) |
              out['ticker'].astype(str).str.contains(query,case=False,regex=False))
        out=out.loc[mask]
    if fundamental:out=out[out['fundamental_ready'].eq('Yes')]
    if valuation:out=out[out['valuation_ready'].eq('Yes')]
    if scored:out=out[out['research_score'].notna()]
    return out.copy()


def _join(values):
    return ' | '.join(sorted({str(x).strip() for x in values if pd.notna(x) and str(x).strip() and str(x).strip().lower() not in ('not provided','other / unclassified')}))


def build_memberships(holdings):
    """One verified U.S. issuer row; country-qualified issuer ID avoids ticker collisions."""
    from holdings_intelligence import display_strategy
    required={'issuer_id','company','ticker','country','portfolio_id','category','fund_title','weight'}
    if not required.issubset(holdings.columns):
        raise ValueError(f'Holdings missing fields: {sorted(required-set(holdings.columns))}')
    h=holdings.loc[holdings['category'].isin(['sector','factor'])].copy()
    h=h[h['country'].str.strip().str.casefold().isin(['united states','usa','us','united states of america'])]
    if h.empty:return pd.DataFrame()
    h['type_label']=[display_strategy(t,'USA Factor' if c=='factor' else 'USA Sector') for t,c in zip(h.fund_title,h.category)]
    h['weight']=pd.to_numeric(h.weight,errors='coerce')
    rows=[]
    for issuer,g in h.groupby('issuer_id',sort=True):
        distinct=g.drop_duplicates(subset=['portfolio_id'])
        s=distinct[distinct.category=='sector']; f=distinct[distinct.category=='factor']
        labels_s=_join(s.type_label); labels_f=_join(f.type_label)
        rows.append(dict(company_key=str(issuer),company=str(g.iloc[0].company),ticker=str(g.iloc[0].ticker),
            country='United States',sectors=labels_s,factors=labels_f,
            funds=_join(distinct.fund_title),
            sector_count=len(items(labels_s)),factor_count=len(items(labels_f)),
            membership_count=int(distinct.portfolio_id.nunique()),
            avg_weight=round(float(distinct.weight.mean()),4) if distinct.weight.notna().any() else None,
            holdings_asof=max(g.as_of.astype(str)) if 'as_of' in g else '',
            industry='',revenue=None,net_income=None,revenue_yoy=None,roe=None,
            operating_margin=None,operating_cash_flow=None,free_cash_flow=None,
            debt_to_equity=None,pe=None,pb=None,price=None,market_cap=None,
            quality_score=None,growth_score=None,valuation_score=None,research_score=None,
            fundamental_ready='No',valuation_ready='No',
            readiness_reason='SEC financials have not been summarized',financial_period='',sec_cik=''))
    return pd.DataFrame(rows)


def load_research():
    source=STORE/'latest_holdings.parquet'
    if not source.exists():return pd.DataFrame(),f'Missing {source.relative_to(ROOT)} — run verified iShares holdings refresh'
    try:
        base=build_memberships(pd.read_parquet(source))
    except (OSError,ValueError,KeyError,ImportError) as exc:
        return pd.DataFrame(),f'Cannot read verified USA holdings: {exc}'
    if base.empty:return base,'No USA companies in verified sector/factor holdings'
    origin='Verified iShares holdings'
    if OUT.exists():
        financial=pd.read_csv(OUT,dtype={'company_key':str},low_memory=False)
        # Enrich only company IDs that still appear in the *current* verified holdings.
        fields=['company_key','industry','revenue','net_income','revenue_yoy','roe','operating_margin',
                'operating_cash_flow','free_cash_flow','debt_to_equity','pe','pb','price','market_cap',
                'quality_score','growth_score','valuation_score','research_score',
                'fundamental_ready','valuation_ready','readiness_reason','financial_period','sec_cik']
        financial=financial[[c for c in fields if c in financial]].drop_duplicates('company_key')
        base=base.drop(columns=[c for c in financial.columns if c!='company_key'],errors='ignore').merge(
            financial,on='company_key',how='left',validate='one_to_one')
        origin+=' + cached SEC financial snapshot'
    for col in NUMBERS:
        if col not in base:base[col]=pd.NA
        base[col]=pd.to_numeric(base[col],errors='coerce')
    for col in ['fundamental_ready','valuation_ready']:
        base[col]=base.get(col,pd.Series(index=base.index,dtype=object)).fillna('No')
    for col in ['industry','financial_period','readiness_reason','sec_cik']:
        if col not in base:base[col]=''
        base[col]=base[col].fillna('').astype(str)
    return base,origin


def summary_table(frame):
    cols=['company','ticker','sectors','sector_count','factors','factor_count','membership_count',
          'avg_weight','roe','revenue_yoy','operating_margin','pe','pb',
          'quality_score','growth_score','valuation_score','research_score','readiness_reason']
    x=frame.reindex(columns=cols).copy()
    for col in ['roe','revenue_yoy','operating_margin']:x[col]=x[col]*100
    return x.rename(columns={'company':'Company','ticker':'Ticker','sectors':'Sectors',
        'sector_count':'# Sectors','factors':'Factors','factor_count':'# Factors',
        'membership_count':'# Source ETFs','avg_weight':'Avg ETF Weight (%)',
        'roe':'ROE %','revenue_yoy':'Revenue Growth %','operating_margin':'Operating Margin %',
        'pe':'P/E','pb':'P/B','quality_score':'Quality','growth_score':'Growth',
        'valuation_score':'Valuation','research_score':'Research Score','readiness_reason':'Data Quality'})
