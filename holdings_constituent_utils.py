"""Factor constituent consensus: transparent, offline-testable, no synthetic holdings."""
from __future__ import annotations
import io
import re
import pandas as pd
import numpy as np

FACTORS = {
 'Global': {'Value':'IWVL','Growth':'IWFG','Momentum':'IMTM','Quality':'IQLT','Low Volatility':'ACWV','Size':'ISZE','Dividend':'IDV'},
 'USA': {'Value':'IVE','Growth':'IVW','Momentum':'MTUM','Quality':'QUAL','Low Volatility':'USMV','Size':'IWM','Dividend':'VYM'},
 'India': {'Value':'NIFTY50_VALUE20','Momentum':'NIFTY200_MOMENTUM30','Quality':'NIFTY200_QUALITY30','Low Volatility':'NIFTY100_LOWVOL30','Alpha':'NIFTY_ALPHA50','Equal Weight':'NIFTY50_EQUALWEIGHT'}
}
REQUIRED = ('factor','company','weight')
ALIASES = {'factor':['factor','fund','index','etf','strategy'], 'company':['company','name','security name','issuer name','holding','company name'], 'ticker':['ticker','symbol','security ticker'], 'isin':['isin'], 'weight':['weight','weight (%)','weight(%)','weight %','portfolio weight','% of net assets','weightage','weightage (%)'], 'as_of':['as_of','as of','holdings date','date'], 'source':['source','provider']}

def parse_holdings(file, factor=None, source=None):
    """Accept canonical CSV/XLSX or common issuer/NSE header variants."""
    name = getattr(file,'name','upload.csv').lower()
    if name.endswith(('.xlsx','.xls')):
        df = pd.read_excel(file)
    else:
        data=file.read() if hasattr(file,'read') else file
        if isinstance(data,str): data=data.encode('utf-8')
        df=None
        for skip in (0,1,2,3,4,5,6,7,8,9,10):
            try:
                candidate=pd.read_csv(io.BytesIO(data),skiprows=skip,encoding='utf-8-sig',on_bad_lines='skip')
                cols={str(c).strip().lower() for c in candidate.columns}
                if cols.intersection(ALIASES['company']) and cols.intersection(ALIASES['weight']):
                    df=candidate;break
            except (ValueError,UnicodeError,pd.errors.ParserError): continue
        if df is None: raise ValueError('No recognizable company and weight columns. Use the provided CSV template.')
    rename={}
    for c in df.columns:
        key=str(c).strip().lower().replace('_',' ')
        for target,variants in ALIASES.items():
            if key in variants:rename[c]=target;break
    df=df.rename(columns=rename)
    if factor is not None:df['factor']=factor
    if source is not None:df['source']=source
    missing=set(REQUIRED)-set(df.columns)
    if missing:raise ValueError('Missing required columns: '+', '.join(sorted(missing)))
    for optional in ('ticker','isin','as_of','source'):
        if optional not in df:df[optional]=''
    df=df[list(REQUIRED)+['ticker','isin','as_of','source']].copy()
    df['weight']=pd.to_numeric(df['weight'].astype(str).str.replace('%','',regex=False).str.replace(',','',regex=False).str.strip(),errors='coerce')
    df=df.dropna(subset=['weight'])
    df['company']=df['company'].astype(str).str.strip()
    df['factor']=df['factor'].astype(str).str.strip()
    df=df[(df.company!='') & (df.company.str.lower()!='nan') & (df.weight>0)]
    if df.empty:raise ValueError('No positive constituent weights found.')
    return df.reset_index(drop=True)

def _identity(row):
    isin=str(row['isin']).strip().upper()
    if isin and isin not in ('NAN','NONE'):return 'ISIN:'+isin
    ticker=str(row['ticker']).strip().upper()
    if ticker and ticker not in ('NAN','NONE','-'):return 'TICKER:'+ticker
    name=re.sub(r'[^A-Z0-9]+',' ',str(row['company']).upper()).strip()
    return 'NAME:'+name

def score_holdings(raw, selected_factors, mode='All holdings', weights=(.4,.35,.25), min_count=1):
    """Full-universe ranks first; missing factors score zero; equal factor influence."""
    factors=list(dict.fromkeys(selected_factors))
    if not factors:raise ValueError('Select at least one factor.')
    if len(weights)!=3 or any(w<0 for w in weights) or not np.isclose(sum(weights),1):raise ValueError('Score weights must sum to 1.')
    d=raw[raw.factor.isin(factors)].copy()
    if d.empty:return pd.DataFrame(),pd.DataFrame()
    d['id']=d.apply(_identity,axis=1)
    if d.duplicated(['factor','id']).any():
        dup=d.loc[d.duplicated(['factor','id'],keep=False),['factor','company']]
        raise ValueError('Duplicate constituents within factor: '+', '.join(dup.factor.unique()))
    d['weight']=pd.to_numeric(d.weight,errors='coerce')
    if d.weight.isna().any() or (d.weight<=0).any():raise ValueError('Weights must be positive numbers.')
    totals=d.groupby('factor').weight.sum()
    if (totals>102).any():raise ValueError('Factor weight total exceeds 102%; check duplicate records or percentage units.')
    d['rank']=d.groupby('factor').weight.rank(ascending=False,method='min').astype(int)
    n=d.groupby('factor').id.transform('size')
    d['rank_score']=np.where(n>1,100*(1-(d['rank']-1)/(n-1)),100.)
    d['weight_multiple']=d.weight*n/100
    d['weight_score']=100*np.minimum(d.weight_multiple,5)/5
    d['top10']=d['rank']<=10
    count=d.groupby('id').factor.nunique().rename('Factor Count')
    top=d[d.top10].groupby('id').factor.nunique().rename('Top-10 Count')
    agg=d.groupby('id').agg(**{'Company':('company','first'),'Ticker':('ticker','first'),'ISIN':('isin','first'),'Average Weight %':('weight','mean'),'Sum of Factor Weights %':('weight','sum')})
    agg=agg.join(count).join(top).fillna({'Top-10 Count':0})
    agg['Top-10 Count']=agg['Top-10 Count'].astype(int)
    agg['Breadth Score']=100*agg['Factor Count']/len(factors)
    agg['Rank Strength']=d.groupby('id').rank_score.sum()/len(factors)
    agg['Weight Strength']=d.groupby('id').weight_score.sum()/len(factors)
    a,b,c=weights
    agg['Consensus Score']=a*agg['Breadth Score']+b*agg['Rank Strength']+c*agg['Weight Strength']
    agg['Factors']=d.groupby('id').factor.apply(lambda s:', '.join(sorted(s)))
    if mode=='Top 10 only':agg=agg[agg['Top-10 Count']>0]
    agg=agg[agg['Factor Count']>=min_count].sort_values(['Consensus Score','Factor Count','Average Weight %'],ascending=False).reset_index().rename(columns={'id':'Company ID'})
    agg.insert(0,'Rank',np.arange(1,len(agg)+1))
    return agg,d


