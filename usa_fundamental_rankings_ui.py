"""Read-only, source-audited USA fundamental rankings inside Financial KPIs.

No network collection runs in Streamlit. GitHub Actions creates the CSV.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'data/usa_research/fundamental_rankings.csv'
EVIDENCE = ROOT / 'data/usa_research/fundamental_field_evidence.csv'
LINKS = ROOT / 'data/usa_research/financial_source_links.csv'
FIELDS = ['roe','current_ratio','operating_margin','net_margin','eps_growth_pct']
LABELS = {'company':'Company','ticker':'Ticker','sectors':'Sector','factors':'Factor',
          'roe':'ROE %','current_ratio':'Current Ratio','operating_margin':'Operating Margin %',
          'net_margin':'Net Margin %','eps_growth_pct':'EPS Growth %',
          'total_fundamental_rank':'Total Rank','market_cap':'Market Cap (USD)',
          'market_cap_rank':'Market Cap Rank','final_rank':'Final Rank',
          'financial_period':'Financial Period', 'ranking_reason':'Status'}
for _field,_label in list(LABELS.items()):
    if _field in FIELDS: LABELS[_field+'_rank'] = _label.replace(' %','')+' Rank'

@st.cache_data(ttl=600,show_spinner=False)
def _load(path: str, stamp: float):
    return pd.read_csv(path, low_memory=False, dtype={'ticker':str,'company_key':str})

def _get(path: Path):
    return _load(str(path),path.stat().st_mtime) if path.is_file() else pd.DataFrame()

def _split(v):
    if not isinstance(v,str):return []
    return [x.strip() for x in v.split('|') if x.strip()]

def render_usa_fundamental_rankings():
    st.markdown('### 🏅 Fundamental Rankings')
    st.caption('SEC annual filings · Five separate ranks · Lowest rank sum wins · Market cap breaks ties only. Not an investment recommendation.')
    df=_get(SOURCE)
    if df.empty:
        st.info('Ranking data has not been published. The scheduled USA financial workflow builds data/usa_research/fundamental_rankings.csv.')
        return
    required={'company','ticker','ranking_eligible','final_rank','total_fundamental_rank',*FIELDS}
    missing=required-set(df.columns)
    if missing:
        st.warning('Ranking dataset missing required fields: '+', '.join(sorted(missing)))
        return
    ranked=df['ranking_eligible'].astype(str).str.lower().isin(['true','yes','1'])
    c1,c2,c3=st.columns(3)
    c1.metric('Verified companies',f'{len(df):,}')
    c2.metric('Fully ranked',f'{ranked.sum():,}')
    c3.metric('Incomplete / ineligible',f'{(~ranked).sum():,}')
    if not ranked.any():
        st.warning('No companies currently qualify for all five individual ranks. The full verified-company table is shown so you can inspect available metrics and missing evidence.')
    with st.expander('Rankings filters',expanded=True):
        left,mid,right=st.columns([1,1,1])
        sectors=sorted({s for value in df.get('sectors',pd.Series(dtype=object)) for s in _split(value)})
        selected_sector=left.multiselect('Sector',sectors,key='usa_fr_sector')
        show=mid.selectbox('Ranking status',['All verified companies','Ranked only','Incomplete only'],key='usa_fr_status')
        search=right.text_input('Search company / ticker',key='usa_fr_search').strip()
    view=df.copy()
    if selected_sector:view=view[view['sectors'].fillna('').map(lambda x:bool(set(_split(x))&set(selected_sector)))]
    if show=='Ranked only':view=view[view['ranking_eligible'].astype(str).str.lower().isin(['true','yes','1'])]
    elif show=='Incomplete only':view=view[~view['ranking_eligible'].astype(str).str.lower().isin(['true','yes','1'])]
    if search:view=view[view['company'].fillna('').astype(str).str.contains(search,case=False,regex=False)|view['ticker'].fillna('').astype(str).str.contains(search,case=False,regex=False)]
    view=view.sort_values(['final_rank','ticker'],na_position='last',kind='stable')
    cols=['company','ticker','sectors']
    for k in FIELDS:cols += [k,k+'_rank']
    cols += ['total_fundamental_rank','market_cap','market_cap_rank','final_rank','financial_period','ranking_reason']
    cols=[c for c in cols if c in view.columns]
    shown=view[cols].rename(columns=LABELS)
    # Financial values in percent units already; DO NOT multiply by 100 again.
    st.dataframe(shown,hide_index=True,use_container_width=True,height=440)
    st.download_button('Download visible fundamental rankings (CSV)',shown.to_csv(index=False).encode('utf-8'),file_name='usa_fundamental_rankings_filtered.csv',mime='text/csv',key='usa_fr_download')
    with st.expander('Individual company evidence and source links',expanded=False):
        if not len(view):return
        entries=[f"{r['company']} ({r['ticker']})" for _,r in view.iterrows()]
        chosen=st.selectbox('Inspect source values',entries,key='usa_fr_source_company')
        ix=entries.index(chosen)
        record=view.iloc[ix]
        st.write('Ticker:',record['ticker'],' | Reporting period:',record.get('financial_period','N/A'))
        ev=_get(EVIDENCE)
        if not ev.empty and 'company_key' in ev:
            subset=ev[ev['company_key'].astype(str)==str(record.get('company_key',''))]
            st.dataframe(subset,hide_index=True,use_container_width=True)
        links=_get(LINKS)
        if not links.empty and 'company_key' in links:
            subset=links[links['company_key'].astype(str)==str(record.get('company_key',''))]
            if len(subset):
                st.caption('External company research links (not scraped into the ranking):')
                for k,url in subset.iloc[0].items():
                    if k.endswith('_url') and isinstance(url,str) and url.startswith('https://'):
                        st.markdown(f'[{k.replace("_url","").replace("_"," ").title()}]({url})')
    st.caption('Banks/financial firms and companies missing any of the five metrics are unranked. Company size never contributes to the fundamental sum. Year-end ROE uses period-end equity. Ranking is within the eligible USA universe, not a valuation signal.')
