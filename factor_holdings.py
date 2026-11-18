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


def render_factor_holdings():
    import streamlit as st
    import plotly.express as px
    st.title('Factor Holdings Comparison')
    st.caption('Cross-factor company consensus using published constituent weights. Not a prediction or a measure of actual capital flows.')
    market=st.selectbox('Market',['Global','USA','India'],key='holdings_market')
    available=FACTORS[market]
    factors=st.multiselect('Factors',list(available),default=list(available),key='holdings_factors')
    st.info('Upload current, complete constituent-weight files from official ETF issuers (Global/USA) or Nifty Indices (India). No fabricated holdings or silent Yahoo price-data substitution. The dashboard does not yet automatically fetch issuer holdings.')
    with st.expander('Data requirements and template',expanded=False):
        st.markdown('One CSV/XLSX per factor, or one combined CSV. Required: **factor, company, weight** (percent, e.g. `2.5` for 2.5%). Recommended: **ticker, isin, as_of, source**. For single-factor files, choose the matching factor below. Use consistent reporting dates and complete holdings; partial files bias rankings.')
        template=pd.DataFrame([{'factor':'Value','company':'Illustrative Company A','ticker':'DEMO','isin':'','weight':2.5,'as_of':'2026-11-01','source':'Example only — not real holdings'}])
        st.download_button('Download CSV template',template.to_csv(index=False).encode(),'factor_holdings_template.csv','text/csv')
    uploads=st.file_uploader('Upload constituent holdings CSV / XLSX',type=['csv','xlsx'],accept_multiple_files=True,key=f'holdings_upload_{market}')
    parsed=[];errors=[]
    for f in uploads:
        with st.expander('File mapping: '+f.name,expanded=True):
            chosen=st.selectbox('Factor for this file', ['Use factor column']+list(available),key=f'factor_map_{market}_{f.name}')
            try:
                frame=parse_holdings(f,factor=None if chosen=='Use factor column' else chosen,source=f.name)
                unknown=set(frame.factor)-set(available)
                if unknown:raise ValueError('Unknown factor labels: '+', '.join(sorted(unknown)))
                st.caption(f'{len(frame):,} rows · '+', '.join(sorted(frame.factor.unique())))
                parsed.append(frame)
            except Exception as exc:errors.append(f'{f.name}: {exc}')
    for e in errors:st.error(e)
    if not parsed:
        st.warning('No holdings data loaded. Upload official constituent-weight files to calculate company rankings.')
        return
    raw=pd.concat(parsed,ignore_index=True)
    coverage=raw.groupby('factor').agg(Holdings=('company','size'),Weight_Total_Percent=('weight','sum'),As_Of=('as_of',lambda x:', '.join(sorted(set(str(v) for v in x if str(v).strip())))),Source=('source',lambda x:', '.join(sorted(set(str(v) for v in x))))).reset_index()
    missing=set(factors)-set(raw.factor)
    if missing:st.warning('Missing selected factors (no invented zeros in denominator): '+', '.join(sorted(missing)))
    incomplete=coverage[coverage.Weight_Total_Percent.between(0,95,inclusive='left')]
    if not incomplete.empty:st.warning('Potentially incomplete factor files (total weights below 95%): '+', '.join(incomplete.factor))
    if (coverage.Weight_Total_Percent>102).any():st.error('Weight totals above 102%; check source files and percentage units.');return
    effective=[f for f in factors if f in set(raw.factor)]
    if not effective:st.warning('None of the selected factors have uploaded data.');return
    c1,c2,c3,c4=st.columns(4)
    with c1:mode=st.selectbox('Holdings view',['All holdings','Top 10 only'])
    with c2:min_count=st.number_input('Minimum factor count',1,len(effective),min(2,len(effective)))
    with c3:top_n=st.selectbox('Top N',[10,20,30,50,100],index=1)
    with c4:st.caption('Score weights below')
    a,b,c=st.columns(3)
    with a:breadth=st.slider('Breadth %',0,100,40)
    with b:rank=st.slider('Rank %',0,100,35)
    with c:weight=st.slider('Weight %',0,100,25)
    if breadth+rank+weight!=100:st.error('Scoring weights must add to 100%.');return
    try:result,detail=score_holdings(raw,effective,mode,(breadth/100,rank/100,weight/100),min_count)
    except ValueError as exc:st.error(str(exc));return
    k1,k2,k3,k4=st.columns(4)
    k1.metric('Companies in ranking',len(result))
    k2.metric('Factors with data',f'{len(effective)}/{len(factors)}')
    k3.metric('Multi-factor companies',int((result['Factor Count']>=2).sum()) if len(result) else 0)
    k4.metric('Highest ranked',result.iloc[0].Company if len(result) else '—')
    st.subheader('Holdings coverage and source validation')
    st.dataframe(coverage,use_container_width=True,hide_index=True)
    if len(result):
        left,right=st.columns([1.6,1])
        with left:
            fig=px.bar(result.head(top_n).sort_values('Consensus Score'),x='Consensus Score',y='Company',orientation='h',hover_data=['Factor Count','Top-10 Count'])
            fig.update_layout(template='plotly_dark',height=max(360,min(900,28*min(top_n,len(result))+120)),margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig,use_container_width=True)
        with right:
            counts=result.groupby('Factor Count').size().reset_index(name='Companies')
            fig=px.bar(counts,x='Factor Count',y='Companies',title='Factor count distribution')
            fig.update_layout(template='plotly_dark',height=360)
            st.plotly_chart(fig,use_container_width=True)
        st.subheader('Company factor exposure matrix — weight %')
        matrix=detail.pivot(index='id',columns='factor',values='weight')
        matrix=matrix.reindex(index=result['Company ID'].head(top_n)).rename(index=result.set_index('Company ID')['Company'].to_dict())
        st.dataframe(matrix.style.format('{:.2f}%',na_rep='—'),use_container_width=True)
        st.subheader('Consensus company ranking')
        st.dataframe(result.drop(columns=['Company ID']).round(3),use_container_width=True,hide_index=True)
        st.download_button('Download company ranking CSV',result.to_csv(index=False).encode(),f'{market.lower()}_factor_consensus.csv','text/csv')
        st.subheader('Selected company factor profile')
        ids=result['Company ID'].tolist()
        chosen=st.selectbox('Company',ids,format_func=lambda x:result.set_index('Company ID').loc[x,'Company'])
        profile=detail[detail.id==chosen][['factor','weight','rank','rank_score','weight_multiple','top10','as_of','source']].sort_values('rank')
        st.dataframe(profile.rename(columns={'factor':'Factor','weight':'Weight %','rank':'Within-Factor Rank','rank_score':'Rank Score','weight_multiple':'Weight Multiple','top10':'Top 10','as_of':'As Of','source':'Source'}),use_container_width=True,hide_index=True)
    st.subheader('Raw uploaded holdings')
    st.dataframe(raw,use_container_width=True,hide_index=True)
    st.download_button('Download raw holdings CSV',raw.to_csv(index=False).encode(),f'{market.lower()}_factor_holdings_raw.csv','text/csv')
    st.caption('Factor count uses all constituents. Top-10 mode filters companies but does not recompute ranks. Scores use all loaded factors in the selected market; missing factors are excluded with a warning. Validate complete coverage and as-of dates before interpreting.')
