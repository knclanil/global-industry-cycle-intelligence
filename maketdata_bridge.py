"""Read-only adapter for MaketData v4 normalized MongoDB collections."""
import os
from functools import lru_cache
from datetime import datetime

FIELDS = ('revenue','gross_profit','operating_income','net_income','eps_basic','eps_diluted','assets','liabilities','equity','cash','current_assets','current_liabilities','long_term_debt','short_term_debt','operating_cash_flow','capex')

@lru_cache(maxsize=1)
def connection():
    from pymongo import MongoClient
    uri = os.getenv('MONGODB_URI')
    if not uri:
        try:
            import streamlit as st
            uri = st.secrets.get('MONGODB_URI')
        except (ImportError, FileNotFoundError, KeyError):
            pass
    if not uri:
        raise RuntimeError('MONGODB_URI not configured in Streamlit Secrets')
    client = MongoClient(uri, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000, socketTimeoutMS=15000, retryWrites=False)
    dbname = os.getenv('MONGODB_DATABASE')
    if not dbname:
        try:
            import streamlit as st
            dbname = st.secrets.get('MONGODB_DATABASE', 'maketdata')
        except (ImportError, FileNotFoundError, KeyError):
            dbname = 'maketdata'
    return client[dbname]

def fetch(tickers, annual=6, quarterly=20, db=None):
    """Batch query only the verified MaketData collection names; no writes."""
    db = db if db is not None else connection()
    requested = sorted({str(t).strip().upper().replace('-', '.') for t in tickers if t})
    if not requested:
        return {}
    query = {'ticker': {'$in': requested}}
    companies = list(db['companies'].find(query, {'_id':0}))
    by_ticker = {str(c.get('ticker','')).upper(): {'company':c,'annual':[],'quarterly':[]} for c in companies}
    # Some normalized rows may exist before company metadata is populated.
    for kind, cap in [('annual',annual),('quarterly',quarterly)]:
        rows = db['financial_'+kind].find(query, {'_id':0}).sort('period_end', -1)
        for row in rows:
            ticker = str(row.get('ticker','')).upper()
            entry = by_ticker.setdefault(ticker, {'company':{'ticker':ticker},'annual':[],'quarterly':[]})
            if len(entry[kind]) < cap:
                entry[kind].append(row)
    return by_ticker

def safe_div(a,b):
    try:
        if a is None or b is None or float(b)==0: return None
        return float(a)/float(b)
    except (ValueError,TypeError,OverflowError,ZeroDivisionError):return None

def change(current, prior):
    return None if prior is None or float(prior)<=0 or current is None else safe_div(float(current)-float(prior),abs(float(prior)))

def metrics(entry, price=None, market_cap=None):
    """Only same-period observations; annual flows never mixed with quarterly."""
    annual = sorted(entry.get('annual',[]),key=lambda r:r.get('period_end',''),reverse=True)
    if not annual:return {}, 0
    valid = [r for r in annual if isinstance(r.get('metrics'),dict) and not r.get('critical_invalid') and r.get('quality_status') not in ('critical','invalid')]
    if not valid:return {}, 0
    latest=valid[0]['metrics']; previous=valid[1]['metrics'] if len(valid)>1 else {}
    g=lambda key:latest.get(key)
    debt=(g('long_term_debt') or 0)+(g('short_term_debt') or 0) if (g('long_term_debt') is not None or g('short_term_debt') is not None) else None
    fcf=(g('operating_cash_flow')-abs(g('capex'))) if g('operating_cash_flow') is not None and g('capex') is not None else None
    eps=g('eps_diluted') if g('eps_diluted') is not None else g('eps_basic')
    prior_eps=previous.get('eps_diluted') if previous.get('eps_diluted') is not None else previous.get('eps_basic')
    out={
      'Revenue growth YoY':change(g('revenue'),previous.get('revenue')),
      'EPS growth':change(eps,prior_eps),
      'Net income growth':change(g('net_income'),previous.get('net_income')),
      'Operating cash flow growth':change(g('operating_cash_flow'),previous.get('operating_cash_flow')),
      'Free cash flow growth':None,
      'Gross margin':safe_div(g('gross_profit'),g('revenue')),
      'Operating margin':safe_div(g('operating_income'),g('revenue')),
      'Net margin':safe_div(g('net_income'),g('revenue')),
      'ROE':safe_div(g('net_income'),g('equity')),
      'ROA':safe_div(g('net_income'),g('assets')),
      'Debt / Equity':safe_div(debt,g('equity')),
      'Debt / Assets':safe_div(debt,g('assets')),
      'Current ratio':safe_div(g('current_assets'),g('current_liabilities')),
      'Cash / Debt':safe_div(g('cash'),debt),
      'Operating cash flow':g('operating_cash_flow'),
      'Free cash flow':fcf,
      'FCF margin':safe_div(fcf,g('revenue')),
      'Operating cash flow / Net income':safe_div(g('operating_cash_flow'),g('net_income')),
      'Capex intensity':safe_div(abs(g('capex')) if g('capex') is not None else None,g('revenue')),
      'P/E':safe_div(price,eps),
      'P/B':safe_div(market_cap,g('equity')),
      'P/S':safe_div(market_cap,g('revenue')),
      'FCF yield':safe_div(fcf,market_cap),
    }
    if len(valid)>1:
        pm=valid[1]['metrics']
        pf=(pm['operating_cash_flow']-abs(pm['capex'])) if pm.get('operating_cash_flow') is not None and pm.get('capex') is not None else None
        out['Free cash flow growth']=change(fcf,pf)
    for n in (3,5):
        val=None
        if len(valid)>n:
            now,then=g('revenue'),valid[n]['metrics'].get('revenue')
            if now is not None and then is not None and now>0 and then>0:
                val=(now/then)**(1/n)-1
        out[f'Revenue CAGR {n}Y']=val
    for field in ('Revenue growth YoY','EPS growth','Net income growth','Operating cash flow growth','Free cash flow growth','Gross margin','Operating margin','Net margin','ROE','ROA','Debt / Equity','Debt / Assets','Current ratio','Cash / Debt','Operating cash flow','Free cash flow','FCF margin','Operating cash flow / Net income','Capex intensity','P/E','P/B','P/S','FCF yield','Revenue CAGR 3Y','Revenue CAGR 5Y'):
        if out.get(field) is not None:
            import math
            if not math.isfinite(float(out[field])):out[field]=None
    return out, len(valid)

CATEGORIES = {
 'Growth': ('Revenue growth YoY','Revenue CAGR 3Y','Revenue CAGR 5Y','EPS growth','Net income growth','Operating cash flow growth','Free cash flow growth'),
 'Profitability': ('Gross margin','Operating margin','Net margin','ROE','ROA'),
 'Financial Strength': ('Debt / Equity','Debt / Assets','Current ratio','Cash / Debt'),
 'Cash Flow Quality': ('FCF margin','Operating cash flow / Net income','Capex intensity','Free cash flow growth'),
 'Valuation': ('P/E','P/B','P/S','FCF yield')
}
DEFAULT_WEIGHTS={'Growth':.25,'Profitability':.25,'Financial Strength':.20,'Cash Flow Quality':.20,'Valuation':.10}
LOWER={'Debt / Equity','Debt / Assets','Capex intensity','P/E','P/B','P/S'}

def score_universe(rows, weights=None, min_category_coverage=.5):
    """Peer percentiles; missing categories make score N/A, never zero."""
    weights=weights or DEFAULT_WEIGHTS
    if abs(sum(weights.values())-1)>1e-6:raise ValueError('Weights must sum to 1')
    output={t:{'categories':{},'score':None,'coverage':0} for t in rows}
    for category, fields in CATEGORIES.items():
        for ticker, vals in rows.items():
            available=[f for f in fields if vals.get(f) is not None]
            output[ticker]['categories'][category]=None
            output[ticker].setdefault('_points',{})[category]=[]
            output[ticker].setdefault('_coverage',{})[category]=len(available)/len(fields)
        for field in fields:
            peers=sorted([(t,float(v[field])) for t,v in rows.items() if v.get(field) is not None],key=lambda x:x[1])
            if len(peers)<2:continue
            for t,v in peers:
                less=sum(x<v for _,x in peers); equal=sum(x==v for _,x in peers)
                percentile=100*(less+(equal-1)/2)/(len(peers)-1)
                output[t]['_points'][category].append(100-percentile if field in LOWER else percentile)
        for t in rows:
            if output[t]['_coverage'][category]>=min_category_coverage and output[t]['_points'][category]:
                output[t]['categories'][category]=sum(output[t]['_points'][category])/len(output[t]['_points'][category])
    for t, item in output.items():
        item['coverage']=sum(item['_coverage'][c]*len(CATEGORIES[c]) for c in CATEGORIES)/sum(map(len,CATEGORIES.values()))
        if all(item['categories'][c] is not None for c in CATEGORIES):
            item['score']=sum(weights[c]*item['categories'][c] for c in CATEGORIES)
        del item['_points'];del item['_coverage']
    return output
