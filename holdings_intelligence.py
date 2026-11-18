"""Verified iShares holdings snapshots and issuer-level leadership ranking."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
STORE=ROOT/'data'/'holdings'
FACTORS=['239695','239728','256101','239563','239725','239710','251614']
SECTORS=['239505','239511','239506','239524','239508','239507','239520','239503','239523','239514','239522']
GLOBAL_FACTORS=['271538','275382','239499','239605','271540']
GLOBAL_SECTORS=['239740','239744','239753','239739','239742','239741','239751','239745','239748','239750']
GROUPS={**{p:'USA Factor' for p in FACTORS},**{p:'USA Sector' for p in SECTORS},**{p:'Global Sector' for p in GLOBAL_SECTORS},**{p:'Global Factor' for p in GLOBAL_FACTORS}}
SOURCES={**{p:'factor' for p in FACTORS},**{p:'sector' for p in SECTORS}}
ALL_SOURCES={**SOURCES, **{p:'global_sector' for p in GLOBAL_SECTORS},**{p:'global_factor' for p in GLOBAL_FACTORS}}
BASE_URL='https://www.blackrock.com/varnish-api/blk-one01-product-data/product-data/api/v1/get-fund-document'

def url_for(pid,asof):
    from urllib.parse import urlencode
    return BASE_URL+'?'+urlencode(dict(appType='PRODUCT_PAGE',appSubType='ISHARES',targetSite='us-ishares',locale='en_US',portfolioId=pid,userType='individual',asOfDate=asof,component='holdings'))

def normalize(frame,pid,asof,fund_title=None):
    """Fail closed on unrecognized files; do not infer missing issuers or weights."""
    df=frame.copy()
    df.columns=[str(c).strip().lower().replace(' ','_').replace('%','pct') for c in df.columns]
    def col(*names):
        return next((x for x in names if x in df),None)
    name=col('name','company','security_name','issuer_name'); weight=col('weight_(pct)','weight_pct','weight','portfolio_weight','weightage')
    ticker=col('ticker','symbol'); isin=col('isin'); asset=col('asset_class','assetclass')
    country=col('location','country','country_of_risk','domicile'); sector=col('sector','gics_sector')
    if not name or not weight:raise ValueError('Unrecognized holdings columns (issuer name/weight required)')
    if not ticker and not isin:raise ValueError('Ticker or ISIN required to identify issuers safely')
    out=pd.DataFrame({'company':df[name].astype(str).str.strip(),'ticker':df[ticker].astype(str).str.strip().str.upper() if ticker else '',
        'isin':df[isin].astype(str).str.strip().str.upper() if isin else '',
        'weight':pd.to_numeric(df[weight].astype(str).str.replace('%','',regex=False).str.replace(',','',regex=False),errors='coerce'),
        'portfolio_id':pid,'category':ALL_SOURCES[pid],'group':GROUPS[pid],
        'fund_title':str(fund_title or '').strip(),'as_of':asof,
        'country':df[country].astype(str).str.strip() if country else 'Not provided',
        'sector':df[sector].astype(str).str.strip() if sector else 'Not provided'})
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

def rank_companies(current,previous=None, factor_ids=None, factor_category="factor", sector_category="sector"):
    """Rank one geographic universe without mixing its ETF holdings with another."""
    if factor_ids is None: factor_ids = FACTORS
    if current.empty:return pd.DataFrame(),pd.DataFrame()
    d=current.copy(); d['weight']=pd.to_numeric(d.weight)
    # ETF-specific weight strength, capped at each ETF's 90th percentile.
    thresholds=d.groupby('portfolio_id').weight.transform(lambda x:max(float(x.quantile(.9)),1e-8))
    d['conviction']=np.minimum(1,d.weight/thresholds)
    factors=d[d.category==factor_category]; sectors=d[d.category==sector_category]
    rows=[]
    for issuer,grp in d.groupby('issuer_id'):
        fg=factors[factors.issuer_id==issuer]; sg=sectors[sectors.issuer_id==issuer]
        breadth=fg.portfolio_id.nunique()/len(factor_ids)
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
        # Use the issuer's largest verified ETF exposure as the source for
        # descriptive attributes. Do not infer country from ETF domicile.
        representative=grp.sort_values('weight',ascending=False).iloc[0]
        country_name=str(representative.get('country','Not provided')).strip()
        sector_name=str(representative.get('sector','Not provided')).strip()
        rows.append(dict(issuer_id=issuer,company=grp.company.iloc[0],ticker=grp.ticker.iloc[0],
            country=country_name if country_name and country_name.lower()!='nan' else 'Not provided',
            sector=sector_name if sector_name and sector_name.lower()!='nan' else 'Not provided',
            factor_count=int(fg.portfolio_id.nunique()),
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
            if a is None: event='added'; points=8 if ALL_SOURCES[pid]==factor_category else 4
            elif b is None:event='removed';points=-10 if ALL_SOURCES[pid]==factor_category else -6
            else:
                delta=float(b.weight)-float(a.weight)
                if abs(delta)<.10 or abs(delta)/max(float(a.weight),.01)<.05:continue
                event='increased' if delta>0 else 'decreased'
                points=(min(4,4*delta) if delta>0 else max(-5,5*delta)) if ALL_SOURCES[pid]==factor_category else (min(3,3*delta) if delta>0 else max(-4,4*delta))
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


def display_strategy(fund_title, group):
    """Human-readable strategy label; never expose source portfolio identifiers."""
    title = str(fund_title or '').lower()
    if group in ('USA Factor', 'Global Factor'):
        for phrase, label in [('min vol', 'Minimum Volatility'), ('minimum volatility', 'Minimum Volatility'),
                              ('momentum', 'Momentum'), ('quality', 'Quality'), ('value', 'Value'), ('multifactor', 'Multifactor'), ('multi-factor', 'Multifactor'), ('dividend', 'Dividend'),
                              ('growth', 'Growth'), ('size', 'Size'), ('small-cap', 'Small Cap'),
                              ('russell 2000', 'Small Cap / Broad Market'), ('multifactor', 'Multifactor'),
                              ('multi-factor', 'Multifactor')]:
            if phrase in title: return label
        return 'Other / Unclassified'
    if group in ('USA Sector', 'Global Sector'):
        for phrase, label in [('information technology', 'Information Technology'), ('technology', 'Technology'),
                              ('tech', 'Technology'), ('health care', 'Health Care'), ('healthcare', 'Health Care'),
                              ('financial', 'Financials'), ('consumer discretionary', 'Consumer Discretionary'),
                              ('consumer staples', 'Consumer Staples'), ('communication', 'Communication Services'),
                              ('industrial', 'Industrials'), ('materials', 'Materials'), ('energy', 'Energy'),
                              ('utilities', 'Utilities'), ('real estate', 'Real Estate'),
                              ('semiconductor', 'Semiconductors')]:
            if phrase in title: return label
        return 'Other / Unclassified'
    return 'Other / Unclassified'


def holdings_display_table(frame):
    """Readable holdings table without internal identifiers or numeric category codes."""
    data = frame.copy()
    if 'group' not in data: data['group'] = data.get('category', 'Other')
    if 'fund_title' not in data: data['fund_title'] = ''
    data['Type / Sector'] = [display_strategy(title, group) for title, group in zip(data.fund_title, data.group)]
    columns = ['group', 'Type / Sector', 'fund_title', 'ticker', 'company', 'country', 'sector', 'weight', 'as_of']
    data = data[[c for c in columns if c in data.columns]]
    return data.rename(columns={'group':'Group', 'fund_title':'iShares Fund',
                                'ticker':'Ticker', 'company':'Company', 'country':'Country', 'sector':'Sector',
                                'weight':'Weight (%)', 'as_of':'Holdings as of'})


def ranking_display_table(ranking, holdings, region='USA'):
    """Replace portfolio-ID lists with human-readable fund names in ranking tables."""
    data = ranking.copy()
    names = holdings[['portfolio_id', 'fund_title', 'group']].drop_duplicates('portfolio_id').copy()
    name_map = dict(zip(names.portfolio_id.astype(str), names.fund_title))
    for column, output in [('factor_etfs', f'{region} Factor Funds'), ('sector_etfs', f'{region} Sector Funds')]:
        if column in data:
            data[output] = data[column].fillna('').map(
                lambda value: ', '.join(name_map.get(x.strip(), 'Fund name unavailable')
                                        for x in str(value).split(',') if x.strip()))
            data = data.drop(columns=[column])
    return data.drop(columns=['issuer_id'], errors='ignore').rename(columns={
        'country':'Country', 'sector':'Sector',
        'factor_count':'Factor Fund Coverage', 'factor_conviction':'Relative Factor Weight',
        'sector_rank':'Sector Position', 'sector_leader':'Sector Leader',
        'base_score':'Base Score', 'change_score':'Holdings Change Score',
        'final_score':'Leadership Score', 'rank':'Rank', 'company':'Company', 'ticker':'Ticker'})


def render_leadership_tab(st, region, ranking, holdings):
    """Independent, searchable company leaderboard with its own exposure drilldown."""
    prefix = region.lower()
    region_holdings = holdings[holdings.category.isin(
        ['factor','sector'] if region == 'USA' else ['global_factor','global_sector'])].copy()
    st.subheader(f'{region} Company Holdings Leadership')
    if ranking.empty:
        st.info(f'No verified {region} leadership rankings saved yet. Run the holdings refresh to populate this table.')
        return
    st.caption('Factor breadth 45% · relative factor weight 40% · sector position 15%. Rankings are exposure signals, not evidence of purchases or sales.')
    a,b,c = st.columns(3)
    a.metric('Ranked companies', f'{len(ranking):,}')
    b.metric('Verified iShares funds', region_holdings.portfolio_id.nunique())
    c.metric('Latest holdings as of', max(region_holdings.as_of.astype(str)) if not region_holdings.empty else 'N/A')
    ranking = ranking.copy()
    ranking['Leadership state'] = ranking.apply(leadership_state, axis=1)
    controls = st.columns([2,2,1])
    query = controls[0].text_input(f'Search {region} company or ticker', key=f'{prefix}_leader_query')
    state = controls[1].selectbox('Leadership state', ['All', *sorted(ranking['Leadership state'].unique())], key=f'{prefix}_leader_state')
    top = controls[2].selectbox('Rows', [20,50,100,500,3000,10000], index=1, key=f'{prefix}_leader_rows')
    filtered = ranking
    if query:
        filtered = filtered[filtered.company.astype(str).str.contains(query,case=False,regex=False) |
                            filtered.ticker.astype(str).str.contains(query,case=False,regex=False)]
    if state != 'All': filtered = filtered[filtered['Leadership state'] == state]
    display = ranking_display_table(filtered, region_holdings, region=region)
    # Factor types are derived only from the current region's verified factor ETF titles.
    # Do not mix Global Factor exposures with USA Factor exposures.
    factor_category = 'factor' if region == 'USA' else 'global_factor'
    factor_positions = region_holdings[region_holdings.category == factor_category].copy()
    if not factor_positions.empty and {'issuer_id', 'fund_title', 'group'}.issubset(factor_positions.columns):
        factor_positions['factor_type'] = [
            display_strategy(title, group)
            for title, group in zip(factor_positions.fund_title, factor_positions.group)
        ]
        factor_types = factor_positions.groupby('issuer_id')['factor_type'].agg(
            lambda values: ', '.join(sorted({str(v) for v in values if v and v != 'Other / Unclassified'}))
            or 'Other / Unclassified'
        )
        display['Factor'] = filtered.issuer_id.map(factor_types).fillna('Not held in factor funds').values
    else:
        display['Factor'] = 'Not provided'
    # Older ranking snapshots predate the country/sector fields. Enrich from
    # verified holdings without mixing USA and Global exposure universes.
    if 'Country' not in display.columns or 'Sector' not in display.columns:
        lookup = region_holdings.sort_values('weight',ascending=False).drop_duplicates('issuer_id').set_index('issuer_id')
        for source, label in [('country','Country'),('sector','Sector')]:
            if label not in display.columns:
                if source in lookup.columns:
                    display[label] = filtered.issuer_id.map(lookup[source]).fillna('Not provided').values
                else:
                    display[label] = 'Not provided'
    ordered = ['Rank','Company','Ticker','Country','Sector','Factor']
    display = display[[c for c in ordered if c in display.columns] + [c for c in display.columns if c not in ordered]]
    st.dataframe(display.head(top), hide_index=True, use_container_width=True)
    st.download_button(f'Download {region} rankings CSV', display.to_csv(index=False).encode(),
                       file_name=f'{prefix}_company_leadership.csv', mime='text/csv', key=f'{prefix}_leader_download')
    st.subheader(f'{region} company ETF exposure')
    candidates = ranking[['issuer_id','ticker','company']].copy()
    candidates['label'] = candidates.ticker.astype(str) + ' — ' + candidates.company.astype(str)
    selected = st.selectbox('Select company', candidates.index.tolist(),
                            format_func=lambda i: candidates.loc[i,'label'], key=f'{prefix}_leader_company')
    positions = region_holdings[region_holdings.issuer_id == candidates.loc[selected,'issuer_id']].sort_values('weight',ascending=False)
    if positions.empty: st.info('No verified ETF positions available for this issuer.')
    else: st.dataframe(holdings_display_table(positions),hide_index=True,use_container_width=True)
    changes_path = STORE / ('latest_changes.parquet' if region == 'USA' else 'global_latest_changes.parquet')
    if changes_path.exists():
        changes = pd.read_parquet(changes_path)
        with st.expander(f'{region} latest verified exposure changes'):
            if changes.empty: st.info('No material verified changes in the latest comparison.')
            else: st.dataframe(changes.drop(columns=['portfolio_id','issuer_id'],errors='ignore'),hide_index=True,use_container_width=True)


def render_holdings_intelligence():
    import streamlit as st
    st.title('🏆 Company Holdings Leadership Intelligence')
    st.caption('Verified BlackRock iShares portfolio exposures · USA and Global rankings calculated independently')
    holdings_path = STORE / 'latest_holdings.parquet'
    if not holdings_path.exists():
        st.warning('Holdings have not been committed to the deployed app. Run the Verified iShares holdings refresh workflow.')
        return
    holdings = pd.read_parquet(holdings_path)
    holdings['portfolio_id'] = holdings.portfolio_id.astype(str)
    holdings['group'] = holdings.portfolio_id.map(GROUPS)
    if 'fund_title' not in holdings: holdings['fund_title'] = ''
    usa_path = STORE / 'company_rankings.parquet'
    global_path = STORE / 'global_company_rankings.parquet'
    usa = pd.read_parquet(usa_path) if usa_path.exists() else pd.DataFrame()
    global_ranking = pd.read_parquet(global_path) if global_path.exists() else pd.DataFrame()
    usa_tab, global_tab = st.tabs(['🇺🇸 USA Leadership', '🌍 Global Leadership'])
    with usa_tab: render_leadership_tab(st, 'USA', usa, holdings)
    with global_tab: render_leadership_tab(st, 'Global', global_ranking, holdings)
    st.subheader('iShares holdings by fund group')
    for group_name in ['USA Factor','USA Sector','Global Factor','Global Sector']:
        group_data = holdings[holdings.group == group_name]
        with st.expander(group_name):
            if group_data.empty:
                st.info('No verified holdings loaded for this group yet. Refresh the iShares holdings sources.')
                continue
            funds = group_data[['fund_title','as_of']].drop_duplicates().copy()
            funds['fund_title'] = funds.fund_title.fillna('').astype(str).str.strip()
            funds = funds[funds.fund_title != ''].sort_values('fund_title')
            if funds.empty:
                st.warning('Verified holdings exist, but fund titles are missing. Run the holdings refresh.')
                continue
            label = 'Factor Type' if 'Factor' in group_name else 'Sector'
            funds[label] = funds.fund_title.map(lambda title: display_strategy(title, group_name))
            st.dataframe(funds[['fund_title',label,'as_of']].rename(columns={'fund_title':'iShares Fund','as_of':'Holdings as of'}),hide_index=True,use_container_width=True)
            chosen = st.selectbox('View fund holdings', funds.fund_title.tolist(), key='fund_'+group_name)
            st.dataframe(holdings_display_table(group_data[group_data.fund_title==chosen].sort_values('weight',ascending=False)),hide_index=True,use_container_width=True)
    with st.expander('Methodology and data integrity'):
        st.write('USA Factor + USA Sector form the USA score. Global Factor + Global Sector form the Global score. Each score uses the configured factor ETF denominator, even during provisional coverage.')
        st.write('Reported portfolio weights do not establish institutional transactions, cash flows or discretionary conviction. Missing or unverified ETF documents never imply security removals.')
