"""SEC XBRL financial statements. v2.4.0 | 2026-11-05.
Uses SEC companyfacts, caches on disk, never invents missing facts.
Annual facts require FY and 10-K/10-K/A; quarterly facts require Q1-Q3 and 10-Q/10-Q/A.
Not all XBRL concepts are comparable across issuers. Amounts are USD unless labeled otherwise.
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'data' / 'sec_cache'
FUNDAMENTALS = ROOT / 'data' / 'fundamentals'
BASE = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'
TICKERS = 'https://www.sec.gov/files/company_tickers.json'

def _user_agent():
    agent = os.getenv('SEC_USER_AGENT', '').strip()
    if agent:
        return agent
    try:
        import streamlit as st
        agent = str(st.secrets.get('SEC_USER_AGENT', '')).strip()
        if agent:
            return agent
        return str(st.secrets.get('sec', {}).get('user_agent', '')).strip()
    except Exception:
        return ''

MAX_AGE = 24 * 3600

# Ordered fallbacks: do not add unrelated concepts as synonyms.
TAGS = {
 'Revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','Revenues','SalesRevenueNet','SalesRevenueGoodsNet','SalesRevenueServicesNet','SalesRevenueNetOfReturnsAndAllowances'],
 'Cost of revenue': ['CostOfRevenue','CostOfGoodsAndServicesSold','CostOfGoodsSold','CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization'],
 'Gross profit': ['GrossProfit'],
 'Operating income': ['OperatingIncomeLoss'],
 'Selling general and administrative': ['SellingGeneralAndAdministrativeExpense'],
 'Research and development': ['ResearchAndDevelopmentExpense'],
 'Income before tax': ['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest','IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments'],
 'Income tax expense': ['IncomeTaxExpenseBenefit'],
 'Interest expense': ['InterestExpenseNonOperating','InterestExpense'],
 'Interest income': ['InvestmentIncomeInterest','InterestIncomeExpenseAfterProvisionForLoanLoss'],
 'Net income': ['NetIncomeLoss'],
 # Banking-specific SEC GAAP concepts. Exact concepts are logged in diagnostics.
 'Bank interest income': ['InterestAndDividendIncomeOperating','InterestIncomeExpenseOperating','InterestIncomeExpenseAfterProvisionForLoanLoss'],
 'Bank interest expense': ['InterestExpense','InterestExpenseDeposits','InterestExpenseBorrowings','InterestExpenseOperating'],
 'Net interest income': ['InterestIncomeExpenseNet'],
 'Noninterest income': ['NoninterestIncome','NoninterestIncomeOther'],
 'Provision for credit losses': ['ProvisionForLoanLeaseAndOtherLosses','ProvisionForCreditLosses','ProvisionForLoanLeaseAndOtherLossesNet'],
 'Noninterest expense': ['NoninterestExpense','NoninterestExpenseOther'],

 'Diluted EPS': ['EarningsPerShareDiluted'],
 'Cash and equivalents': ['CashAndCashEquivalentsAtCarryingValue'],
 'Current assets': ['AssetsCurrent'],
 'Total assets': ['Assets'],
 'Current liabilities': ['LiabilitiesCurrent'],
 'Total liabilities': ['Liabilities'],
 'Stockholders equity': ['StockholdersEquity'],
 'Long-term debt': ['LongTermDebtCurrent','LongTermDebtNoncurrent'],
 'Operating cash flow': ['NetCashProvidedByUsedInOperatingActivities'],
 'Capital expenditures': ['PaymentsToAcquirePropertyPlantAndEquipment'],
 'Investing cash flow': ['NetCashProvidedByUsedInInvestingActivities'],
 'Financing cash flow': ['NetCashProvidedByUsedInFinancingActivities'],
 'Dividends paid': ['PaymentsOfDividends','PaymentsOfDividendsCommonStock'],
 'Share repurchases': ['PaymentsForRepurchaseOfCommonStock'],
}
BANK_STATEMENT = ['Bank interest income','Bank interest expense','Net interest income',
                  'Noninterest income','Revenue','Provision for credit losses',
                  'Noninterest expense','Income before tax','Income tax expense','Net income','Diluted EPS']
BANK_TICKERS = {'JPM','BAC','WFC','C','GS','MS','USB','PNC','TFC','COF','BK','STT','SCHW','FITB','KEY','RF','HBAN'}

def is_bank(data, ticker=None):
    """Detect bank reporting using multiple banking-specific SEC concepts.

    Ticker fallback covers common banks; this is NOT a complete SIC classifier.
    """
    gaap = data.get('facts', {}).get('us-gaap', {})
    signature = sum(bool(gaap.get(tag)) for tag in
                    ('InterestIncomeExpenseNet','NoninterestIncome','NoninterestExpense',
                     'InterestAndDividendIncomeOperating'))
    return signature >= 2 or str(ticker or '').upper() in BANK_TICKERS

INSTANT = {'Cash and equivalents','Current assets','Total assets','Current liabilities','Total liabilities','Stockholders equity','Long-term debt'}
EPS = {'Diluted EPS'}
STATEMENTS = {
 'Income Statement':['Revenue','Cost of revenue','Gross profit','Selling general and administrative','Research and development','Operating income','Income before tax','Income tax expense','Interest expense','Interest income','Net income','Diluted EPS'],
 'Balance Sheet':['Cash and equivalents','Current assets','Total assets','Current liabilities','Total liabilities','Stockholders equity','Long-term debt'],
 'Cash Flow':['Operating cash flow','Capital expenditures','Free cash flow','Investing cash flow','Financing cash flow','Dividends paid','Share repurchases'],
}

def _read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f'Invalid cached SEC file {path}: {exc}') from exc


def _get(url, cache_file):
    # The Streamlit page must never depend on SEC network access.
    if cache_file.exists():
        return _read_json(cache_file)
    raise RuntimeError(
        'SEC financial data is not cached for this company. '
        'Run the SEC fundamentals GitHub Actions workflow, then redeploy. '
        'The Streamlit viewer intentionally makes no live SEC requests.'
    )


def _directory():
    for path in (FUNDAMENTALS / 'sec_company_directory.json',
                 CACHE / 'company_tickers.json'):
        if path.exists():
            raw = _read_json(path)
            if isinstance(raw, list):
                return raw
            if isinstance(raw, dict):
                return list(raw.values())
    raise RuntimeError(
        'SEC company directory is not cached. Run the SEC fundamentals '
        'GitHub Actions workflow and commit data/fundamentals/sec_company_directory.json.'
    )


def resolve_cik(ticker):
    ticker = str(ticker).strip().upper().replace('.', '-')
    matches = [item for item in _directory()
               if str(item.get('ticker', '')).upper().replace('.', '-') == ticker]
    if len(matches) == 1:
        item = matches[0]
        return int(item['cik_str']), item.get('title', ticker)
    if len(matches) > 1:
        raise ValueError(f'Ambiguous SEC CIK mapping for {ticker}.')
    return None, None


def load_company(ticker):
    cik, name = resolve_cik(ticker)
    if cik is None:
        raise ValueError(f'No SEC CIK match for {ticker}; SEC coverage may be unavailable.')
    # Reuse the existing background fundamentals pipeline output first.
    for path in (FUNDAMENTALS / f'facts_{cik:010d}.json',
                 CACHE / f'CIK{cik:010d}.json'):
        if path.exists():
            return _read_json(path), cik, name
    raise RuntimeError(
        f'No cached SEC Company Facts for {ticker} (CIK {cik:010d}). '
        'Run the SEC fundamentals GitHub Actions workflow to collect this issuer.'
    )

def _facts(data, label, cadence='annual'):
    """Select a consistent fiscal-period fact, not the first tag with any history.

    SEC `fy`/`fp` describe filing context and can refer to a later fiscal year
    than the comparative fact's `end`. Group by actual fact end dates instead.
    """
    taxonomy = data.get('facts', {}).get('us-gaap', {})
    unit = 'USD/shares' if label in EPS else 'USD'
    candidates = {}
    for priority, tag in enumerate(TAGS[label]):
        for row in taxonomy.get(tag, {}).get('units', {}).get(unit, []):
            form = row.get('form')
            end = row.get('end')
            val = row.get('val')
            if not end or not isinstance(val, (int, float)) or isinstance(val, bool):
                continue
            if cadence == 'annual' and form not in ('10-K', '10-K/A'):
                continue
            if cadence != 'annual' and form not in ('10-Q', '10-Q/A'):
                continue
            start = row.get('start')
            if label in INSTANT:
                if start:
                    continue
            else:
                if not start:
                    continue
                try:
                    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
                except (ValueError, TypeError):
                    continue
                if cadence == 'annual' and not 300 <= days <= 380:
                    continue
                if cadence != 'annual' and not 65 <= days <= 110:
                    continue
            # Keep the true period end; never confuse comparative FY facts.
            period = end if cadence == 'annual' else end
            filed = row.get('filed', '')
            # Prefer the most recent filing for the same tag/period, then
            # the highest-priority tag. Do not mix different taxonomy tags
            # across periods without retaining provenance.
            score = (-priority, filed, row.get('accn', ''))
            current = candidates.get(period)
            if current is None or score > current[0]:
                candidates[period] = (score, (float(val), filed, end, tag))
    return {period: record for period, (_, record) in candidates.items()}


def diagnostics(data, cadence='annual', periods=6):
    """Show actual SEC concepts, dates, and missing metrics for debugging."""
    records=[]
    for label in TAGS:
        found=_facts(data,label,cadence)
        for period in sorted(found,reverse=True)[:periods]:
            val,filed,end,tag=found[period]
            records.append({'Metric':label,'Period end':period,'Status':'Available',
                            'SEC concept':tag,'Filed':filed,'Value':val})
        if not found:
            records.append({'Metric':label,'Period end':'—','Status':'Missing',
                            'SEC concept':'—','Filed':'—','Value':None})
    return pd.DataFrame(records)

def statements(data,cadence='annual',periods=6,ticker=None):
    result={}
    bank=is_bank(data,ticker)
    for statement,base_labels in STATEMENTS.items():
        labels = BANK_STATEMENT if bank and statement == 'Income Statement' else base_labels
        rows={label:_facts(data,label,cadence) for label in labels if label!='Free cash flow'}
        # FCF = operating cash flow - positive capex outflows, not investing cash flow.
        ocf=rows.get('Operating cash flow',{})
        capex=rows.get('Capital expenditures',{})
        rows['Free cash flow']={p:(o[0]-abs(capex[p][0]),max(o[1],capex[p][1]),o[2],'derived') for p,o in ocf.items() if p in capex}
        # v2.3.5: derive gross profit once in the canonical statement layer.
        # This same table feeds the income statement, overview, Sankey and scores.
        # Only use revenue and cost of revenue for the SAME fiscal period.
        if statement == 'Income Statement' and not bank:
            revenue = rows.get('Revenue', {})
            cost = rows.get('Cost of revenue', {})
            gross = rows.get('Gross profit', {})
            for period in revenue.keys() & cost.keys():
                if period in gross:
                    continue  # A reported SEC GrossProfit fact always takes precedence.
                r, c = revenue[period][0], cost[period][0]
                if r >= 0 and c >= 0 and r >= c:
                    gross[period] = (
                        r - c,
                        max(revenue[period][1], cost[period][1]),
                        period,
                        'derived: Revenue - Cost of revenue',
                    )
            # Do NOT infer operating income from gross profit minus SG&A alone:
            # companies can report additional operating expense classifications.
        if statement == 'Income Statement' and bank:
            # Derive only from aligned, explicitly reported components.
            # Do not equate net interest income after provisions with interest income.
            ii, ie, nii = (rows.get(k,{}) for k in ('Bank interest income','Bank interest expense','Net interest income'))
            for period in ii.keys() & ie.keys():
                if period not in nii:
                    nii[period] = (ii[period][0]-ie[period][0],
                                   max(ii[period][1],ie[period][1]),period,
                                   'derived: Bank interest income - Bank interest expense')
            rev, other = rows.get('Revenue',{}),rows.get('Noninterest income',{})
            for period in nii.keys() & other.keys():
                if period not in rev:
                    rev[period]=(nii[period][0]+other[period][0],
                                 max(nii[period][1],other[period][1]),period,
                                 'derived: Net interest income + Noninterest income')
            # Dynamic, period-specific bank reconciliation. Never force a
            # reported total to equal a sum of incompatible SEC concepts.
            # Report discrepancies for diagnostics instead of overwriting facts.
            # The UI can display a detailed flow only for reconciled components.
            # Do not manufacture missing provision/expense or substitute 0.
        # v2.3.3: liabilities = assets - equity, a balance-sheet identity.
        # Derived values are explicitly marked and never replace reported facts.
        if statement == 'Balance Sheet':
            assets=rows.get('Total assets',{})
            equity=rows.get('Stockholders equity',{})
            liabilities=rows.get('Total liabilities',{})
            for period in assets.keys() & equity.keys():
                if period not in liabilities:
                    a,e=assets[period][0],equity[period][0]
                    if a>=0 and a-e>=0:
                        liabilities[period]=(a-e,max(assets[period][1],equity[period][1]),period,'derived: Assets - StockholdersEquity')
        # Operating income is not safely inferred from net income or gross profit
        # alone: issuers can have additional operating expense classifications.
        available=sorted(set().union(*(set(v) for v in rows.values())),reverse=True)[:periods]
        table=pd.DataFrame(index=labels,columns=available,dtype=float)
        provenance={}
        for label,values in rows.items():
            for period in available:
                if period in values:
                    table.loc[label,period]=values[period][0]
                    provenance[(label,period)]=values[period][1:]
        result[statement]=(table,provenance)
    return result

def overview(stmts):
    inc=stmts['Income Statement'][0]
    bs=stmts['Balance Sheet'][0]
    cf=stmts['Cash Flow'][0]
    def latest(df,label):
        if label not in df.index:return None
        values=pd.to_numeric(df.loc[label],errors='coerce').dropna()
        return float(values.iloc[0]) if not values.empty else None
    rev=latest(inc,'Revenue'); net=latest(inc,'Net income'); op=latest(inc,'Operating income')
    assets=latest(bs,'Total assets'); liabilities=latest(bs,'Total liabilities'); equity=latest(bs,'Stockholders equity')
    ocf=latest(cf,'Operating cash flow'); fcf=latest(cf,'Free cash flow')
    def ratio(a,b):return 100*a/b if a is not None and b not in (None,0) else None
    return {'Revenue':rev,'Net income':net,'Operating margin %':ratio(op,rev),'Net margin %':ratio(net,rev),'Total assets':assets,'Total liabilities':liabilities,'Equity':equity,'Operating cash flow':ocf,'Free cash flow':fcf}


def bank_reconciliation(income, period, tolerance=0.015):
    """Return transparent same-period bank accounting checks.

    Checks are advisory: SEC tags may have different accounting scopes.
    Missing is never interpreted as zero. No company-specific hardcoding.
    """
    def val(name):
        if name not in income.index or period not in income.columns:
            return None
        x = income.at[name, period]
        return float(x) if pd.notna(x) else None
    ii, ie, nii = (val(x) for x in ('Bank interest income','Bank interest expense','Net interest income'))
    noninterest, rev = val('Noninterest income'), val('Revenue')
    provision, expense = val('Provision for credit losses'), val('Noninterest expense')
    pretax, taxes, net = (val(x) for x in ('Income before tax','Income tax expense','Net income'))
    checks=[]
    def check(name, actual, calculated):
        if actual is None or calculated is None:
            checks.append({'Relationship':name,'Status':'Unavailable','Reported':actual,'Calculated':calculated,'Difference':None})
            return
        diff=actual-calculated
        ok=abs(diff)<=max(1e6,abs(actual)*tolerance)
        checks.append({'Relationship':name,'Status':'Reconciled' if ok else 'Mismatch',
                       'Reported':actual,'Calculated':calculated,'Difference':diff})
    check('Net interest income',nii,ii-ie if ii is not None and ie is not None else None)
    check('Net revenue',rev,nii+noninterest if nii is not None and noninterest is not None else None)
    check('Pretax income',pretax,rev-provision-expense if None not in (rev,provision,expense) else None)
    check('Net income',net,pretax-taxes if None not in (pretax,taxes) else None)
    return pd.DataFrame(checks)
