"""Filing-grounded fundamental research for verified ETF issuers.

SEC XBRL is the authoritative US source. International issuers require an
explicitly configured, licensed provider; no fabricated financial data.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import requests
import time

ROOT = Path(__file__).resolve().parent
STORE = ROOT / 'data' / 'fundamentals'
STORE.mkdir(parents=True, exist_ok=True)
SEC = 'https://data.sec.gov'
TAGS = {
    'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenueFromContractWithCustomerIncludingAssessedTax'],
    'net_income':['NetIncomeLoss'], 'operating_income':['OperatingIncomeLoss'],
    'assets':['Assets'], 'liabilities':['Liabilities'], 'equity':['StockholdersEquity'],
    'cash':['CashAndCashEquivalentsAtCarryingValue'],
    'operating_cash_flow':['NetCashProvidedByUsedInOperatingActivities'],
    'capex':['PaymentsToAcquirePropertyPlantAndEquipment'],
    'debt_current':['LongTermDebtCurrent','LongTermDebtAndCapitalLeaseObligationsCurrent'],
    'debt_long':['LongTermDebtNoncurrent','LongTermDebt'],
    'shares':['CommonStockSharesOutstanding'],
}

def sec_headers():
    identity = os.environ.get('SEC_USER_AGENT', '').strip()
    if not identity or '@' not in identity:
        raise ValueError('Configure SEC_USER_AGENT with a descriptive application name and contact email before refreshing SEC data.')
    return {'User-Agent':identity, 'Accept-Encoding':'gzip, deflate', 'Accept':'application/json'}

def sec_get(path):
    response = requests.get(path, headers=sec_headers(), timeout=25)
    response.raise_for_status()
    return response.json()

def company_directory():
    # SEC-published mapping; match only exact ticker AND company-name similarity.
    data = sec_get('https://www.sec.gov/files/company_tickers.json')
    return pd.DataFrame(data.values())

def resolve_us_company(ticker, company, directory):
    candidates = directory[directory.ticker.astype(str).str.upper() == str(ticker).upper()]
    if len(candidates) != 1:
        return None
    import difflib
    name = str(candidates.iloc[0].title)
    similarity = difflib.SequenceMatcher(None, name.upper(), str(company).upper()).ratio()
    # Avoid silently linking a different issuer with a reused ticker.
    return int(candidates.iloc[0].cik_str) if similarity >= 0.52 else None

def select_facts(facts, tag, currency='USD'):
    """Annual filing observations only; preserve accession and filing dates.

    Filter out quarterly/YTD durations so that an annual number is never
    accidentally compared with a single quarter.
    """
    us = facts.get('facts',{}).get('us-gaap',{})
    for alias in TAGS[tag]:
        entry = us.get(alias, {})
        units = entry.get('units',{})
        values = units.get('shares' if tag == 'shares' else currency, [])
        records = []
        for row in values:
            if row.get('form') not in ('10-K','10-K/A','20-F','20-F/A'):
                continue
            if row.get('fp') != 'FY':
                continue
            start, end = row.get('start'), row.get('end')
            if start and end:
                days = (pd.Timestamp(end) - pd.Timestamp(start)).days
                if not 330 <= days <= 380:
                    continue
            elif tag not in ('assets','liabilities','equity','cash','debt_current','debt_long','shares'):
                continue
            if row.get('val') is None or not row.get('filed') or not end:
                continue
            records.append({'period_end':end,'filed':row['filed'], 'value':float(row['val']),
                            'accession':row.get('accn',''), 'form':row['form'], 'taxonomy_tag':alias})
        if records:
            # Select latest filed observation for each period, including amendments.
            df = pd.DataFrame(records).sort_values(['period_end','filed'])
            return df.drop_duplicates('period_end',keep='last').sort_values('period_end').to_dict('records')
    return []

def extract_company_facts(payload):
    series = {metric:select_facts(payload, metric) for metric in TAGS}
    dates = sorted({r['period_end'] for rows in series.values() for r in rows})
    result = []
    for date in dates:
        row = {'period_end':date}
        for metric, rows in series.items():
            match = next((r for r in rows if r['period_end'] == date),None)
            row[metric] = match['value'] if match else np.nan
            if match:
                row[f'{metric}_filed'] = match['filed']
                row[f'{metric}_accession'] = match['accession']
                row[f'{metric}_tag'] = match['taxonomy_tag']
        result.append(row)
    frame = pd.DataFrame(result)
    if frame.empty: return frame
    frame['free_cash_flow'] = frame.operating_cash_flow - frame.capex
    frame['operating_margin'] = frame.operating_income / frame.revenue.replace(0,np.nan)
    frame['net_margin'] = frame.net_income / frame.revenue.replace(0,np.nan)
    frame['roe'] = frame.net_income / frame.equity.replace(0,np.nan)
    frame['debt'] = frame.debt_current.fillna(0) + frame.debt_long.fillna(0)
    frame['net_debt'] = frame.debt - frame.cash
    frame['fcf_margin'] = frame.free_cash_flow / frame.revenue.replace(0,np.nan)
    frame['cash_conversion'] = frame.operating_cash_flow / frame.net_income.replace(0,np.nan)
    frame['revenue_growth'] = frame.revenue.pct_change(fill_method=None)
    frame['earnings_growth'] = frame.net_income.pct_change(fill_method=None)
    return frame

def load_universe():
    from holdings_intelligence import STORE as HOLDINGS_STORE
    path = HOLDINGS_STORE / 'latest_holdings.parquet'
    if not path.exists(): return pd.DataFrame()
    df = pd.read_parquet(path)
    required = {'issuer_id','ticker','company','country','sector','portfolio_id'}
    if not required.issubset(df.columns): return pd.DataFrame()
    from holdings_intelligence import GROUPS
    df = df.copy()
    df['region'] = df.portfolio_id.astype(str).map(GROUPS).fillna('').map(
        lambda x: 'USA' if x.startswith('USA') else ('Global' if x.startswith('Global') else ''))
    df = df[df.region.ne('')]
    return df[['issuer_id','ticker','company','country','sector','region']].drop_duplicates()

def refresh_us(universe, max_companies=20, directory=None, delay=0.18):
    """Fetch up to max_companies *new* verified US CIKs, checkpointing each.

    Never match a foreign issuer or a ticker without a sufficiently close
    SEC company name. A missing/invalid SEC user agent is a hard failure.
    """
    if universe.empty: return {'updated':0,'skipped':0,'errors':[], 'matched':0}
    sec_headers()  # fail early rather than hiding missing configuration
    if directory is None: directory = company_directory()
    existing = {p.stem for p in STORE.glob('facts_*.json')}
    updated, skipped, matched, errors = 0, 0, 0, []
    seen_ciks = set()
    for row in universe.drop_duplicates('issuer_id').itertuples(index=False):
        if str(row.country).lower() not in ('united states','usa','us'):
            skipped += 1; continue
        cik = resolve_us_company(row.ticker,row.company,directory)
        if cik is None:
            skipped += 1; continue
        if cik in seen_ciks: continue
        seen_ciks.add(cik)
        matched += 1
        key = f'facts_{cik:010d}'
        if key in existing: continue
        if updated >= max_companies: break
        try:
            payload = sec_get(f'{SEC}/api/xbrl/companyfacts/CIK{cik:010d}.json')
            if not isinstance(payload, dict) or not payload.get('facts'):
                raise ValueError('SEC response contains no XBRL facts')
            tmp = STORE/f'{key}.tmp'
            tmp.write_text(json.dumps(payload),encoding='utf-8')
            tmp.replace(STORE/f'{key}.json')
            updated += 1
            time.sleep(max(0.11, delay))
        except (requests.RequestException, ValueError, OSError) as exc:
            errors.append(f'{row.ticker}: {str(exc)[:160]}')
    return {'updated':updated,'skipped':skipped,'matched':matched,'errors':errors}

def available_profiles(universe):
    directory_file = STORE/'sec_company_directory.json'
    if directory_file.exists():
        directory = pd.DataFrame(json.loads(directory_file.read_text()))
    else:
        directory = pd.DataFrame(columns=['ticker','title','cik_str'])
    profiles = []
    for row in universe.itertuples(index=False):
        cik = resolve_us_company(row.ticker,row.company,directory) if not directory.empty and str(row.country).lower() in ('united states','usa','us') else None
        path = STORE/f'facts_{cik:010d}.json' if cik is not None else None
        if path and path.exists():
            try:
                payload = json.loads(path.read_text())
                frame = extract_company_facts(payload)
                if frame.empty: continue
                latest = frame.sort_values('period_end').iloc[-1]
                data = {k:latest.get(k,np.nan) for k in ('roe','operating_margin','net_margin','revenue_growth','earnings_growth','fcf_margin','cash_conversion','net_debt')}
                profiles.append({**row._asdict(),**data,'cik':cik,'period_end':latest.period_end,
                                 'source':'SEC EDGAR XBRL', 'facts_file':str(path.name)})
            except (ValueError, KeyError, TypeError): pass
    return pd.DataFrame(profiles)

def score_profiles(profiles):
    """Transparent sector-relative quality/growth/health/cash score; no valuation without price data.

    A peer cohort with <5 companies is insufficient for percentile ranking.
    Missing metrics are excluded and coverage is shown, never filled with zero.
    """
    if profiles.empty:return profiles.copy()
    df = profiles.copy()
    dimensions = {'Quality':['roe','operating_margin','net_margin'],
                  'Growth':['revenue_growth','earnings_growth'],
                  'Financial health':['net_debt'],
                  'Cash flow':['fcf_margin','cash_conversion']}
    for dim, metrics in dimensions.items():
        parts = []
        for metric in metrics:
            v = pd.to_numeric(df[metric],errors='coerce').replace([np.inf,-np.inf],np.nan)
            # Avoid spurious wins from negative equity, nonpositive earnings, etc.
            if metric in ('roe','cash_conversion'): v = v.where(v.ge(0))
            peer_n = v.groupby(df.sector).transform('count')
            rank = v.groupby(df.sector).rank(pct=True,ascending=(metric=='net_debt'))*100
            parts.append(rank.where(peer_n.ge(5)))
        df[dim] = pd.concat(parts,axis=1).mean(axis=1)
    cols = list(dimensions)
    df['coverage'] = df[cols].notna().sum(axis=1).astype(int)
    # Provisional, not a final investment score: valuation and capital allocation unavailable.
    df['fundamental_score'] = df[cols].mean(axis=1).where(df.coverage.ge(3)).round(1)
    df['status'] = np.where(df.coverage.ge(3),'Provisional (no valuation)','Insufficient coverage')
    return df

def filing_list(cik):
    data = sec_get(f'{SEC}/submissions/CIK{int(cik):010d}.json')
    recent = data.get('filings',{}).get('recent',{})
    rows=[]
    for i, form in enumerate(recent.get('form',[])):
        if form not in ('10-K','10-Q','8-K','10-K/A','10-Q/A','20-F','6-K'):continue
        acc = recent['accessionNumber'][i]
        primary = recent['primaryDocument'][i]
        rows.append({'form':form,'filed':recent['filingDate'][i],
                     'report_date':recent['reportDate'][i],
                     'url':f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-","")}/{primary}'})
    return pd.DataFrame(rows)

def render_fundamental_intelligence():
    import streamlit as st
    st.title('🔎 Fundamental Intelligence')
    st.caption('Source-traceable financial analysis of ETF holdings · official SEC filings · independent USA and Global views')
    universe = load_universe()
    if universe.empty:
        st.warning('No verified holdings snapshot is available. Refresh ETF holdings first; no companies or financial values will be fabricated.')
        return
    with st.expander('Data refresh and coverage',expanded=False):
        st.write('US annual XBRL statements are retrieved from SEC EDGAR on demand. Global filings require an approved provider; unavailable coverage is marked missing.')
        st.caption('Set SEC_USER_AGENT in Streamlit secrets/environment (application name and contact email). Refresh is limited to 20 new issuers per click.')
        if st.button('Refresh up to 20 US issuer filings'):
            try:
                directory = company_directory()
                (STORE/'sec_company_directory.json').write_text(directory.to_json(orient='records'),encoding='utf-8')
                result = refresh_us(universe, directory=directory)
                st.write(result)
                st.cache_data.clear()
            except Exception as exc:st.error(f'SEC refresh unavailable: {exc}')
    @st.cache_data(ttl=3600)
    def cached_profiles():return score_profiles(available_profiles(load_universe()))
    scored = cached_profiles()
    region = st.radio('Holdings universe',['USA','Global'],horizontal=True)
    scope = universe[universe.region.eq(region)]
    st.metric('Unique ETF issuers',scope.issuer_id.nunique())
    status_file = STORE/'refresh_status.json'
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text())
            st.caption(f"Last automated SEC refresh: {status.get('as_of_utc', 'unknown')} · Cached SEC company facts: {status.get('cached_sec_facts', 0)} · Last batch added: {status.get('updated', 0)}")
            if status.get('errors'): st.warning(f"SEC refresh reported {len(status['errors'])} errors. Check refresh_status.json for details.")
        except (ValueError, OSError): pass
    st.metric('Issuers with SEC annual financials',scored[scored.region.eq(region)].issuer_id.nunique() if not scored.empty else 0)
    if scored.empty or scored[scored.region.eq(region)].empty:
        st.info('No verified fundamentals cached for this universe. US issuers can be refreshed from SEC; international coverage requires an additional filings provider.')
        return
    table = scored[scored.region.eq(region)].copy()
    ranking_tab, company_tab, methodology_tab = st.tabs(['Fundamental ranking','Company details & filings','Methodology'])
    with ranking_tab:
        st.warning('Scores are provisional sector-relative comparisons, not complete investment attractiveness rankings. No market valuation feed is connected.')
        st.dataframe(table[['company','ticker','sector','period_end','Quality','Growth','Financial health','Cash flow','fundamental_score','coverage','status']].sort_values('fundamental_score',ascending=False),hide_index=True,use_container_width=True)
        st.download_button('Download fundamentals CSV',table.drop(columns=['facts_file']).to_csv(index=False).encode(),'fundamentals.csv','text/csv')
    with company_tab:
        options = table.sort_values('company').drop_duplicates('issuer_id')
        selected = st.selectbox('Company',options.issuer_id.tolist(),format_func=lambda k: options.loc[options.issuer_id.eq(k),'company'].iloc[0])
        row = options[options.issuer_id.eq(selected)].iloc[0]
        st.subheader(f'{row.company} · {row.ticker}')
        st.caption(f'Source: {row.source} · fiscal period {row.period_end} · coverage {row.coverage}/4')
        raw = json.loads((STORE/row.facts_file).read_text())
        statements = extract_company_facts(raw)
        if not statements.empty:
            st.markdown('#### Financial statements and historical trends')
            cols = [x for x in ['period_end','revenue','operating_income','net_income','assets','liabilities','equity','cash','operating_cash_flow','capex','free_cash_flow','debt','revenue_growth','operating_margin','fcf_margin'] if x in statements]
            st.dataframe(statements[cols].sort_values('period_end',ascending=False),hide_index=True,use_container_width=True)
            st.line_chart(statements.set_index('period_end')[['revenue','net_income','free_cash_flow']])
            with st.expander('Audit trail — source filing accession, taxonomy and filing date'):
                trace_cols = ['period_end']+[c for c in statements if c.endswith(('_filed','_accession','_tag'))]
                st.dataframe(statements[trace_cols],hide_index=True,use_container_width=True)
        st.markdown('#### Official SEC filings')
        if st.button('Load latest filing index'):
            try:st.session_state[f'filings_{row.cik}'] = filing_list(row.cik)
            except Exception as exc:st.error(f'Filing index unavailable: {exc}')
        filings = st.session_state.get(f'filings_{row.cik}')
        if filings is not None and not filings.empty:
            st.dataframe(filings,hide_index=True,use_container_width=True,column_config={'url':st.column_config.LinkColumn('Read original filing')})
            st.caption('Open official filing links to read complete disclosures, management discussion and risk factors. Automated narrative summaries are not enabled.')
        st.info('Financial figures are filing-derived; market price, valuation, analyst estimates and AI filing comparison are not yet connected.')
    with methodology_tab:
        st.markdown((ROOT/'FUNDAMENTAL_INTELLIGENCE_WIKI.md').read_text(encoding='utf-8'))
