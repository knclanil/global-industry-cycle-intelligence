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

def _ticker(value):
    import re
    return re.sub(r'[^A-Z0-9]', '', str(value).upper().strip())


def _name(value):
    import re
    name = str(value).upper().replace('&', ' AND ')
    name = re.sub(r'[^A-Z0-9 ]', ' ', name)
    stop = {'INC','INCORPORATED','CORP','CORPORATION','CO','COMPANY','LTD',
            'LIMITED','PLC','CLASS','CL','COMMON','STOCK','THE','HOLDINGS',
            'HOLDING','GROUP','SA','NV','AG'}
    return ' '.join(x for x in name.split() if x not in stop)


def _is_us(country):
    return str(country).strip().upper() in {
        'US', 'USA', 'UNITED STATES', 'UNITED STATES OF AMERICA', 'U.S.', 'U.S.A.'}


def resolve_us_company(ticker, company, directory):
    """Conservative CIK resolution with normalized ticker and issuer names."""
    if directory.empty or not {'ticker','title','cik_str'}.issubset(directory.columns):
        return None
    key = _ticker(ticker)
    candidates = directory[directory.ticker.astype(str).map(_ticker).eq(key)]
    if len(candidates) != 1:
        return None
    import difflib
    candidate = candidates.iloc[0]
    a, b = _name(candidate.title), _name(company)
    if not a or not b:
        return None
    similarity = difflib.SequenceMatcher(None, a, b).ratio()
    if a != b and similarity < 0.62 and not (len(a) >= 7 and len(b) >= 7 and (a in b or b in a)):
        return None
    return int(candidate.cik_str)


def _cached_cik_index():
    """Use SEC's own CIK/ticker metadata when a directory snapshot is absent."""
    index = {}
    for path in STORE.glob('facts_*.json'):
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            cik = int(payload.get('cik') or path.stem.split('_')[-1])
            name = payload.get('entityName', '')
            for ticker in payload.get('tickers', []):
                index.setdefault(_ticker(ticker), []).append((cik, name))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return index


def _resolve_cached(ticker, company, directory, index):
    cik = resolve_us_company(ticker, company, directory)
    if cik is not None and (STORE / f'facts_{cik:010d}.json').exists():
        return cik
    candidates = index.get(_ticker(ticker), [])
    if len(candidates) == 1:
        cik, name = candidates[0]
        import difflib
        a, b = _name(name), _name(company)
        if a and b and (a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.62):
            return cik
    return None

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
    frame.loc[frame.debt_current.isna() & frame.debt_long.isna(), 'debt'] = np.nan
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
        if not _is_us(row.country):
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

def coverage_diagnostics(universe):
    directory_file = STORE / 'sec_company_directory.json'
    try:
        directory = pd.DataFrame(json.loads(directory_file.read_text())) if directory_file.exists() else pd.DataFrame()
    except (OSError, ValueError):
        directory = pd.DataFrame()
    cached = _cached_cik_index()
    us = universe[universe.country.map(_is_us)].drop_duplicates('issuer_id')
    matched = 0
    with_facts = 0
    with_annual = 0
    samples = []
    for row in us.itertuples(index=False):
        directory_cik = resolve_us_company(row.ticker, row.company, directory)
        if directory_cik is not None:
            matched += 1
        cik = _resolve_cached(row.ticker, row.company, directory, cached)
        if cik is None:
            if len(samples) < 12:
                samples.append({'ticker':row.ticker,'company':row.company,'issue':'No verified CIK / cached facts match'})
            continue
        with_facts += 1
        try:
            payload = json.loads((STORE / f'facts_{cik:010d}.json').read_text())
            frame = extract_company_facts(payload)
            if not frame.empty and frame[[x for x in ('revenue','net_income','assets','operating_cash_flow') if x in frame]].notna().any().any():
                with_annual += 1
            elif len(samples) < 12:
                samples.append({'ticker':row.ticker,'company':row.company,'issue':'Cached facts lack supported annual observations'})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if len(samples) < 12:
                samples.append({'ticker':row.ticker,'company':row.company,'issue':f'Extraction: {str(exc)[:90]}'})
    return {'us_issuers':len(us), 'directory_matched':matched,
            'cached_company_facts':len(list(STORE.glob('facts_*.json'))),
            'holdings_with_cached_facts':with_facts,'holdings_with_annual_data':with_annual,
            'unmatched_samples':samples}


def available_profiles(universe):
    directory_file = STORE/'sec_company_directory.json'
    try:
        directory = pd.DataFrame(json.loads(directory_file.read_text())) if directory_file.exists() else pd.DataFrame()
    except (OSError, ValueError):
        directory = pd.DataFrame()
    cached = _cached_cik_index()
    profiles = []
    for row in universe.itertuples(index=False):
        if not _is_us(row.country):
            continue
        cik = _resolve_cached(row.ticker, row.company, directory, cached)
        path = STORE/f'facts_{cik:010d}.json' if cik is not None else None
        if path and path.exists():
            try:
                payload = json.loads(path.read_text())
                frame = extract_company_facts(payload)
                if frame.empty:
                    continue
                # Prefer the latest fiscal period with at least one real financial value.
                value_cols = [x for x in ('revenue','net_income','assets','operating_cash_flow') if x in frame]
                valid = frame[frame[value_cols].notna().any(axis=1)] if value_cols else frame.iloc[0:0]
                if valid.empty:
                    continue
                latest = valid.sort_values('period_end').iloc[-1]
                data = {k:latest.get(k,np.nan) for k in ('roe','operating_margin','net_margin','revenue_growth','earnings_growth','fcf_margin','cash_conversion','net_debt')}
                profiles.append({**row._asdict(),**data,'cik':cik,'period_end':latest.period_end,
                                 'source':'SEC EDGAR XBRL','facts_file':path.name})
            except (OSError, ValueError, KeyError, TypeError):
                continue
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
    # SEC JSON parsing is expensive: memoize until underlying files change.
    # The fingerprint uses metadata only, so ordinary UI reruns are fast.
    @st.cache_data(show_spinner=False, max_entries=3)
    def _cached_scores(fingerprint, _universe):
        return score_profiles(available_profiles(_universe))

    facts_files = list(STORE.glob('facts_*.json'))
    directory_path = STORE / 'sec_company_directory.json'
    fingerprint = tuple(sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns)
                               for p in facts_files))
    if directory_path.exists():
        fingerprint += ((directory_path.name, directory_path.stat().st_size,
                         directory_path.stat().st_mtime_ns),)
    # Include holdings identity in the key to avoid cross-universe stale results.
    fingerprint += (('holdings', len(universe), int(pd.util.hash_pandas_object(
        universe[['issuer_id','ticker','company','country','region']], index=False).sum())),)
    with st.spinner('Loading cached company fundamentals…'):
        scored = _cached_scores(fingerprint, universe)
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
    with st.expander('SEC matching and extraction diagnostics', expanded=False):
        st.caption('Detailed diagnostics scan all holdings and SEC filings; run only when needed.')
        if st.button('Run detailed diagnostics'):
            with st.spinner('Checking company identifiers and cached statements…'):
                st.session_state['fundamentals_diagnostics'] = coverage_diagnostics(universe)
        diag = st.session_state.get('fundamentals_diagnostics')
        if diag is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('US holdings issuers',diag['us_issuers'])
            c2.metric('CIK matches in SEC directory',diag['directory_matched'])
            c3.metric('Holdings with cached facts',diag['holdings_with_cached_facts'])
            c4.metric('Holdings with annual data',diag['holdings_with_annual_data'])
            st.caption(f"Total SEC fact files: {diag['cached_company_facts']}. The directory-match count includes issuers not yet downloaded.")
            if diag['unmatched_samples']:
                st.dataframe(pd.DataFrame(diag['unmatched_samples']),hide_index=True,use_container_width=True)
            if st.button('Recheck on-disk fundamentals'):
                st.rerun()
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
