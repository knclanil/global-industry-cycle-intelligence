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
    # A ticker is not globally unique. Normalize country for stable identifiers.
    import re
    country_codes = {'United States':'US','United Kingdom':'GB','Australia':'AU',
                     'Spain':'ES','France':'FR','Switzerland':'CH','Germany':'DE',
                     'Japan':'JP','Canada':'CA','Italy':'IT','Netherlands':'NL',
                     'Sweden':'SE','Denmark':'DK','Norway':'NO','Finland':'FI',
                     'Hong Kong':'HK','China':'CN','Taiwan':'TW','South Korea':'KR',
                     'Singapore':'SG','India':'IN','Belgium':'BE','Ireland':'IE',
                     'Israel':'IL','Brazil':'BR','Mexico':'MX','New Zealand':'NZ',
                     'South Africa':'ZA','Portugal':'PT','Austria':'AT'}
    out['country_code'] = out.country.map(country_codes).fillna('')
    # Unknown countries retain their normalized full label, preventing collisions.
    out['country_key'] = out.country_code.where(out.country_code.ne(''),
        out.country.astype(str).str.strip().str.upper())
    out = out[~out.ticker.isin(['','NAN','NONE','-'])].copy()
    out = out[~out.country_key.isin(['','NAN','NONE','NOT PROVIDED','-'])].copy()
    if out.empty: raise ValueError('No equity holdings with verified ticker and country')
    # A ticker occurring in multiple countries gets an explicit country suffix.
    multi_country = out.groupby('ticker').country_key.transform('nunique').gt(1)
    out['display_ticker'] = out.ticker.where(~multi_country,
        out.ticker + '-' + out.country_code.where(out.country_code.ne(''),
            out.country_key.str.replace(r'[^A-Z0-9]', '', regex=True)))
    # Do not silently combine different named companies in the same country.
    conflicts = out.groupby(['ticker','country_key']).company.nunique()
    if (conflicts > 1).any():
        bad = conflicts[conflicts > 1].index.tolist()[:5]
        raise ValueError(f'Conflicting companies for identical ticker and country: {bad}')
    # Aggregate duplicate ticker/country positions *within the same ETF* only.
    # Keep the source record count for auditing and sum weights (not averages).
    keys=['portfolio_id','ticker','country_key']
    out['source_rows'] = 1
    fields={c:'first' for c in out.columns if c not in keys+['weight','source_rows']}
    fields.update({'weight':'sum','source_rows':'sum'})
    out=out.groupby(keys,as_index=False,sort=False).agg(fields)
    # Country-qualified issuer IDs are stable across ETFs; never use ticker alone.
    out['issuer_id']='TICKER_COUNTRY:'+out.ticker+'|'+out.country_key
    out['ticker']=out.display_ticker
    out=out.drop(columns=['display_ticker','country_key','country_code'])
    if out.duplicated(['portfolio_id','issuer_id']).any():
        raise ValueError('Ticker-country consolidation did not yield unique ETF holdings')
    return out.reset_index(drop=True)

def load_etf_performance(path=None):
    """Verified ETF/strategy scores, explicitly keyed by portfolio ID and region.

    CSV columns: portfolio_id, region, performance_score (0..100).
    Missing scores are NOT treated as laggards.
    """
    path = Path(path) if path is not None else STORE / 'etf_performance_scores.csv'
    if not path.exists():
        return {}
    frame = pd.read_csv(path, dtype={'portfolio_id': str, 'region': str})
    required = {'portfolio_id', 'region', 'performance_score'}
    if not required.issubset(frame.columns):
        raise ValueError(f'ETF performance file requires {sorted(required)}')
    frame['performance_score'] = pd.to_numeric(frame.performance_score, errors='raise')
    if frame.performance_score.isna().any() or not frame.performance_score.between(0, 100).all():
        raise ValueError('ETF performance scores must be between 0 and 100')
    frame['region'] = frame.region.astype(str).str.upper().str.strip()
    frame['portfolio_id'] = frame.portfolio_id.astype(str).str.strip()
    if frame.duplicated(['region', 'portfolio_id']).any():
        raise ValueError('Duplicate ETF performance score keys')
    for row in frame.itertuples(index=False):
        expected = 'Global' if row.portfolio_id in GLOBAL_FACTORS + GLOBAL_SECTORS else 'USA'
        if row.portfolio_id not in ALL_SOURCES or row.region != expected.upper():
            raise ValueError(f'ETF score has unknown or mismatched region/ID: {row.region}/{row.portfolio_id}')
    return {(row.region, row.portfolio_id): float(row.performance_score) for row in frame.itertuples(index=False)}


def rank_companies(current, previous=None, factor_ids=None, factor_category='factor',
                   sector_category='sector', performance_scores=None):
    """50/50 performance-weighted sector/factor conviction plus up to 10 breadth points.

    Only verified score matches contribute to a performance component. If none
    are available, a neutral score of 50 is shown and flagged as provisional.
    Missing factor/sector coverage is not scored zero; available side is
    reweighted to 100%. Holdings change events are informational, not a
    second unbounded bonus on the leadership score.
    """
    if factor_ids is None: factor_ids = GLOBAL_FACTORS if factor_category == 'global_factor' else FACTORS
    if current.empty: return pd.DataFrame(), pd.DataFrame()
    region = 'GLOBAL' if factor_category == 'global_factor' else 'USA'
    performance_scores = load_etf_performance() if performance_scores is None else performance_scores
    d = current[current.category.isin([factor_category, sector_category])].copy()
    if d.empty: return pd.DataFrame(), pd.DataFrame()
    d['portfolio_id'] = d.portfolio_id.astype(str)
    d['weight'] = pd.to_numeric(d.weight, errors='coerce')
    d = d.dropna(subset=['weight'])
    thresholds = d.groupby('portfolio_id').weight.transform(lambda x: max(float(x.quantile(.9)), 1e-8))
    d['conviction'] = np.minimum(1, d.weight / thresholds)
    # Scores may be keyed by (region, ETF ID), or simply ETF ID in a test.
    d['performance'] = d.portfolio_id.map(lambda pid: performance_scores.get((region, pid), performance_scores.get(pid, np.nan)))
    d['performance'] = pd.to_numeric(d.performance, errors='coerce')
    d.loc[~d.performance.between(0, 100), 'performance'] = np.nan
    factors = d[d.category == factor_category]; sectors = d[d.category == sector_category]
    universe_size = len(GLOBAL_FACTORS + GLOBAL_SECTORS) if region == 'GLOBAL' else len(FACTORS + SECTORS)

    def component(positions):
        if positions.empty: return np.nan, 0
        valid = positions.dropna(subset=['performance'])
        if valid.empty: return np.nan, 0
        # The conviction factor captures holding size *relative to the ETF*.
        # Average across distinct matched ETFs: adding tiny holdings does not
        # inflate the score by summing repeated exposures.
        value = (valid.conviction * valid.performance).mean()
        return float(value), len(valid)

    rows = []
    for issuer, grp in d.groupby('issuer_id'):
        fg = factors[factors.issuer_id == issuer]
        sg = sectors[sectors.issuer_id == issuer]
        fs, fn = component(fg); ss, sn = component(sg)
        available = [v for v in (ss, fs) if np.isfinite(v)]
        # Explicitly neutral, NOT zero, when no performance source is available.
        alignment = float(np.mean(available)) if available else 50.0
        etf_count = int(grp.portfolio_id.nunique())
        breadth_bonus = 10.0 * np.log1p(etf_count) / np.log1p(universe_size)
        score = min(100.0, alignment + breadth_bonus)
        representative = grp.sort_values('weight', ascending=False).iloc[0]
        sector_rank = None; leader = False
        if not sg.empty:
            best = None
            for _, h in sg.iterrows():
                peers = sectors[sectors.portfolio_id == h.portfolio_id]
                rank = int((peers.weight > h.weight).sum() + 1)
                if best is None or rank < best[0]: best = (rank, len(peers))
            sector_rank = best[0]
            leader = sector_rank <= max(1, int(np.ceil(best[1] * .1)))
        rows.append(dict(issuer_id=issuer, company=representative.company, ticker=representative.ticker,
            country=str(representative.get('country', 'Not provided')),
            sector=str(representative.get('sector', 'Not provided')),
            factor_count=int(fg.portfolio_id.nunique()),
            factor_etfs=', '.join(sorted(fg.portfolio_id.unique())),
            factor_conviction=round(float(fg.conviction.mean()) * 100, 2) if not fg.empty else 0,
            sector_etfs=', '.join(sorted(sg.portfolio_id.unique())),
            sector_rank=sector_rank, sector_leader=bool(leader),
            sector_alignment=round(ss, 2) if np.isfinite(ss) else np.nan,
            factor_alignment=round(fs, 2) if np.isfinite(fs) else np.nan,
            scored_sector_etfs=sn, scored_factor_etfs=fn,
            etf_count=etf_count, breadth_bonus=round(breadth_bonus, 2),
            performance_status='Verified' if fn + sn == etf_count else ('Partial' if fn + sn else 'Missing'),
            base_score=round(alignment, 2)))
    ranking = pd.DataFrame(rows)
    events = []
    if previous is not None and not previous.empty:
        old = previous.set_index(['portfolio_id', 'issuer_id']); new = d.set_index(['portfolio_id', 'issuer_id'])
        for key in sorted(set(old.index) | set(new.index)):
            pid, issuer = key
            a = old.loc[key] if key in old.index else None
            b = new.loc[key] if key in new.index else None
            if a is not None and b is not None and str(a.as_of) == str(b.as_of): continue
            if a is None: event = 'added'
            elif b is None: event = 'removed'
            else:
                delta = float(b.weight) - float(a.weight)
                if abs(delta) < .10 or abs(delta) / max(float(a.weight), .01) < .05: continue
                event = 'increased' if delta > 0 else 'decreased'
            events.append(dict(portfolio_id=pid, issuer_id=issuer,
                company=str((b if b is not None else a).company), event=event,
                previous_weight=float(a.weight) if a is not None else 0.,
                current_weight=float(b.weight) if b is not None else 0.,
                previous_as_of=str(a.as_of) if a is not None else '',
                current_as_of=str(b.as_of) if b is not None else '', points=0.))
    changes = pd.DataFrame(events)
    ranking['change_score'] = 0.0
    ranking['final_score'] = (ranking.base_score + ranking.breadth_bonus).clip(0, 100).round(2)
    ranking = ranking.sort_values(['final_score', 'etf_count', 'issuer_id'],
                                  ascending=[False, False, True]).reset_index(drop=True)
    ranking.insert(0, 'rank', np.arange(1, len(ranking) + 1))
    return ranking, changes

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
        'sector_alignment':'Sector Alignment', 'factor_alignment':'Factor Alignment',
        'etf_count':'ETF Count', 'breadth_bonus':'ETF Breadth Bonus',
        'performance_status':'Performance Data Status',
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
    st.caption('Sector alignment 50% · factor alignment 50% (reweighted if one is unavailable) · up to 10 ETF breadth bonus points. Missing performance data is explicitly flagged. Rankings measure ETF exposure, not company price leadership.')
    a,b,c = st.columns(3)
    a.metric('Ranked companies', f'{len(ranking):,}')
    b.metric('Verified iShares funds', region_holdings.portfolio_id.nunique())
    c.metric('Latest holdings as of', max(region_holdings.as_of.astype(str)) if not region_holdings.empty else 'N/A')
    ranking = ranking.copy()
    if 'performance_status' in ranking and (ranking.performance_status != 'Verified').any():
        st.warning('Some ETF performance scores are missing. Rankings with Partial or Missing status are provisional; supply verified ETF performance scores to compare leaders and laggards.')
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
