"""Verified iShares holdings snapshots and issuer-level leadership ranking."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
STORE=ROOT/'data'/'holdings'
FACTORS=['239695','239728','256101','239563','239725','239710','251614']
SECTORS=['239505','239511','239506','239524','239508','239507','239520','239503','239523','239514','239522']
SOURCES={**{p:'factor' for p in FACTORS},**{p:'sector' for p in SECTORS}}
BASE_URL='https://www.blackrock.com/varnish-api/blk-one01-product-data/product-data/api/v1/get-fund-document'

def url_for(pid,asof):
    from urllib.parse import urlencode
    return BASE_URL+'?'+urlencode(dict(appType='PRODUCT_PAGE',appSubType='ISHARES',targetSite='us-ishares',locale='en_US',portfolioId=pid,userType='individual',asOfDate=asof,component='holdings'))

def normalize(frame,pid,asof):
    """Fail closed on unrecognized files; do not infer missing issuers or weights."""
    df=frame.copy()
    df.columns=[str(c).strip().lower().replace(' ','_').replace('%','pct') for c in df.columns]
    def col(*names):
        return next((x for x in names if x in df),None)
    name=col('name','company','security_name','issuer_name'); weight=col('weight_(pct)','weight_pct','weight','portfolio_weight','weightage')
    ticker=col('ticker','symbol'); isin=col('isin'); asset=col('asset_class','assetclass')
    if not name or not weight:raise ValueError('Unrecognized holdings columns (issuer name/weight required)')
    if not ticker and not isin:raise ValueError('Ticker or ISIN required to identify issuers safely')
    out=pd.DataFrame({'company':df[name].astype(str).str.strip(),'ticker':df[ticker].astype(str).str.strip().str.upper() if ticker else '',
        'isin':df[isin].astype(str).str.strip().str.upper() if isin else '',
        'weight':pd.to_numeric(df[weight].astype(str).str.replace('%','',regex=False).str.replace(',','',regex=False),errors='coerce'),
        'portfolio_id':pid,'category':SOURCES[pid],'as_of':asof})
    if asset:
        valid=df[asset].astype(str).str.lower().str.contains('equity|stock',regex=True)
        out=out.loc[valid]
    out=out.dropna(subset=['weight'])
    out=out[(out.weight>=0)&(out.weight<=100)&(out.company!='')]
    out['issuer_id']=np.where(out['isin'].isin(['','NAN','NONE']), 'TICKER:'+out.ticker,'ISIN:'+out['isin'])
    out=out[~out.issuer_id.isin(['TICKER:','TICKER:NAN','TICKER:NONE'])]
    if out.empty:raise ValueError('No valid equity issuer holdings')
    if out.duplicated(['portfolio_id','issuer_id']).any():
        # A ticker collision is not proof of a shared issuer. Keep distinct
        # names separate and ETF-local until their identities are verified.
        import hashlib
        duplicates = out.duplicated(['portfolio_id','issuer_id'], keep=False)
        out.loc[duplicates, 'issuer_id'] = out.loc[duplicates].apply(
            lambda r: 'UNRESOLVED:'+str(pid)+':'+hashlib.sha256(
                (str(r['ticker'])+'|'+str(r['company'])).encode()).hexdigest()[:20], axis=1)
        if out.duplicated(['portfolio_id','issuer_id']).any():
            raise ValueError('Repeated identical issuer/security identifiers require review')
    return out.reset_index(drop=True)

def rank_companies(current,previous=None):
    if current.empty:return pd.DataFrame(),pd.DataFrame()
    d=current.copy(); d['weight']=pd.to_numeric(d.weight)
    # ETF-specific weight strength, capped at each ETF's 90th percentile.
    thresholds=d.groupby('portfolio_id').weight.transform(lambda x:max(float(x.quantile(.9)),1e-8))
    d['conviction']=np.minimum(1,d.weight/thresholds)
    factors=d[d.category=='factor']; sectors=d[d.category=='sector']
    rows=[]
    for issuer,grp in d.groupby('issuer_id'):
        fg=factors[factors.issuer_id==issuer]; sg=sectors[sectors.issuer_id==issuer]
        breadth=fg.portfolio_id.nunique()/len(FACTORS)
        conviction=float(fg.conviction.mean()) if not fg.empty else 0
        sector_score=0.; sector_rank=None; leader=False
        if not sg.empty:
            scored=[]
            for _,h in sg.iterrows():
                peers=sectors[sectors.portfolio_id==h.portfolio_id].sort_values('weight',ascending=False)
                n=len(peers); rank=int((peers.weight>h.weight).sum()+1)
                scored.append(((n-rank)/(n-1) if n>1 else 1.,rank,rank<=max(1,int(np.ceil(n*.1))),str(h.portfolio_id)))
            sector_score,sector_rank,leader,sector_etf=max(scored,key=lambda v:v[0])
        base=100*(.45*breadth+.40*conviction+.15*sector_score)
        rows.append(dict(issuer_id=issuer,company=grp.company.iloc[0],ticker=grp.ticker.iloc[0],factor_count=int(fg.portfolio_id.nunique()),
            factor_etfs=', '.join(sorted(fg.portfolio_id.unique())),factor_conviction=round(conviction*100,2),
            sector_etfs=', '.join(sorted(sg.portfolio_id.unique())),sector_rank=sector_rank,sector_leader=bool(leader),base_score=round(base,2)))
    ranking=pd.DataFrame(rows)
    events=[]
    if previous is not None and not previous.empty:
        old=previous.set_index(['portfolio_id','issuer_id']); new=d.set_index(['portfolio_id','issuer_id'])
        for key in sorted(set(old.index)|set(new.index)):
            pid,issuer=key
            a=old.loc[key] if key in old.index else None; b=new.loc[key] if key in new.index else None
            if a is not None and b is not None and str(a.as_of)==str(b.as_of):continue
            if a is None: event='added'; points=8 if SOURCES[pid]=='factor' else 4
            elif b is None:event='removed';points=-10 if SOURCES[pid]=='factor' else -6
            else:
                delta=float(b.weight)-float(a.weight)
                if abs(delta)<.10 or abs(delta)/max(float(a.weight),.01)<.05:continue
                event='increased' if delta>0 else 'decreased'
                points=(min(4,4*delta) if delta>0 else max(-5,5*delta)) if SOURCES[pid]=='factor' else (min(3,3*delta) if delta>0 else max(-4,4*delta))
            events.append(dict(portfolio_id=pid,issuer_id=issuer,company=str((b if b is not None else a).company),event=event,
                previous_weight=float(a.weight) if a is not None else 0.,current_weight=float(b.weight) if b is not None else 0.,
                previous_as_of=str(a.as_of) if a is not None else '',current_as_of=str(b.as_of) if b is not None else '',points=round(points,3)))
    changes=pd.DataFrame(events)
    adjustments=changes.groupby('issuer_id').points.sum() if not changes.empty else pd.Series(dtype=float)
    ranking['change_score']=ranking.issuer_id.map(adjustments).fillna(0).clip(-30,30).round(2)
    ranking['final_score']=(ranking.base_score+ranking.change_score).clip(0,100).round(2)
    ranking=ranking.sort_values(['final_score','factor_count','factor_conviction','issuer_id'],ascending=[False,False,False,True]).reset_index(drop=True)
    ranking.insert(0,'rank',np.arange(1,len(ranking)+1))
    return ranking,changes

def read_latest():
    p=STORE/'company_rankings.parquet'
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()

def leadership_state(row):
    """Descriptive state, not a prediction of price performance."""
    change = float(row.get('change_score', 0))
    score = float(row.get('base_score', 0))
    if change >= 3: return 'Strengthening leader' if score >= 35 else 'Emerging exposure'
    if change <= -3: return 'Weakening leader' if score >= 35 else 'Declining exposure'
    return 'Established leader' if score >= 35 else 'Stable / limited exposure'


def render_holdings_intelligence():
    import streamlit as st
    st.title('🏆 Company Holdings Leadership Intelligence')
    st.caption('Verified BlackRock iShares constituent exposures · not institutional transaction or cash-flow data')
    ranking = read_latest()
    holdings_path = STORE / 'latest_holdings.parquet'
    if ranking.empty or not holdings_path.exists():
        st.warning('Rankings are not present in this deployed app. Check data/holdings/company_rankings.parquet in the GitHub branch used by Streamlit, then reboot the app.')
        st.code('data/holdings/company_rankings.parquet')
        return
    holdings = pd.read_parquet(holdings_path)
    coverage = sorted(holdings.portfolio_id.astype(str).unique())
    asofs = sorted(holdings.as_of.astype(str).unique())
    a,b,c,d = st.columns(4)
    a.metric('Ranked companies',f'{len(ranking):,}')
    b.metric('Verified active ETFs',f'{len(coverage)}/{len(SOURCES)}')
    c.metric('Latest holdings as of',max(asofs) if asofs else 'N/A')
    d.metric('Snapshot dates',len(asofs))
    if len(coverage) < len(SOURCES):
        st.warning('Provisional coverage: missing ETFs are not interpreted as removed holdings. Breadth scores use the configured factor denominator.')
    st.caption('Base score: 45% factor breadth + 40% relative factor weight + 15% sector prominence; verified changes adjust up to ±30 points. Weights may change without any trading.')
    ranking=ranking.copy()
    ranking['Leadership state']=ranking.apply(leadership_state,axis=1)
    controls=st.columns([2,2,1])
    query=controls[0].text_input('Search ticker or company',placeholder='e.g. AAPL')
    state=controls[1].selectbox('Leadership state',['All',*sorted(ranking['Leadership state'].unique())])
    top=controls[2].selectbox('Rows',[20,50,100,500,3000],index=1)
    filtered=ranking
    if query:
        mask=filtered['ticker'].astype(str).str.contains(query,case=False,regex=False)|filtered['company'].astype(str).str.contains(query,case=False,regex=False)
        filtered=filtered[mask]
    if state!='All':filtered=filtered[filtered['Leadership state']==state]
    st.dataframe(filtered.head(top),hide_index=True,use_container_width=True)
    st.download_button('Download filtered rankings CSV',filtered.to_csv(index=False).encode(),file_name='company_holdings_rankings.csv',mime='text/csv')
    st.subheader('Company ETF exposure drill-down')
    candidates=ranking[['issuer_id','ticker','company']].copy()
    candidates['label']=candidates['ticker'].astype(str)+' — '+candidates['company'].astype(str)+' ['+candidates['issuer_id'].astype(str)+']'
    chosen=st.selectbox('Select company',candidates['label'].tolist(),index=0)
    issuer=candidates.loc[candidates.label==chosen,'issuer_id'].iloc[0]
    positions=holdings[holdings.issuer_id==issuer].sort_values('weight',ascending=False)
    st.dataframe(positions[['portfolio_id','category','company','ticker','weight','as_of']],hide_index=True,use_container_width=True)
    changes_path=STORE/'latest_changes.parquet'
    if changes_path.exists():
        changes=pd.read_parquet(changes_path)
        st.subheader('Latest verified exposure changes')
        if changes.empty:st.info('No material verified changes in the most recent comparison.')
        else:
            st.dataframe(changes,hide_index=True,use_container_width=True)
            st.download_button('Download changes CSV',changes.to_csv(index=False).encode(),file_name='holdings_changes.csv',mime='text/csv')
    history=STORE/'holding_events.parquet'
    if history.exists():
        events=pd.read_parquet(history)
        with st.expander('Historical event log'):
            st.dataframe(events.tail(1000),hide_index=True,use_container_width=True)
    with st.expander('Data integrity and interpretation'):
        st.write('A verified ETF weight is an observed portfolio allocation, not evidence of discretionary manager conviction, cash inflows, purchases, or sales. Leadership states are descriptive thresholds, not return forecasts. Unresolved issuer identifiers must not be merged across funds.')
        st.write('Active ETFs:',', '.join(coverage))
        st.write('Holdings dates:',', '.join(asofs))
