"""Factor Holdings Intelligence | Buffett/Graham-inspired research | v2.3.0 | 2026-11-05.
Changelog: independent quality and conservative-value evidence; explicit coverage;
optional price-based Graham reference; no fabricated data or investment recommendations.
These are original heuristic research measures, not Buffett/Graham endorsements.
"""
import math
import pandas as pd


def number(df, label, idx=0):
    if df is None or label not in df.index: return None
    vals = pd.to_numeric(df.loc[label], errors='coerce').dropna()
    return float(vals.iloc[idx]) if len(vals)>idx else None


def series(df, label):
    if df is None or label not in df.index: return []
    return [float(v) for v in pd.to_numeric(df.loc[label], errors='coerce').dropna().tolist()]


def safe_div(a,b):
    return a/b if a is not None and b is not None and b!=0 else None


def metric_check(label, value, passed, explanation):
    return {'Indicator':label,'Observed':value,'Pass':passed,'Interpretation':explanation}


def assess(stmts, price=None, shares=None):
    """Evaluate financial statement evidence without imputing absent observations.

    `price` is an explicitly user-supplied, dated USD/share quote; `shares` is an
    explicitly user-supplied current share count. Market valuation is not inferred
    from annual diluted EPS alone when current shares are unavailable.
    """
    inc=stmts['Income Statement'][0]; bs=stmts['Balance Sheet'][0]; cf=stmts['Cash Flow'][0]
    rev=series(inc,'Revenue'); net=series(inc,'Net income'); op=series(inc,'Operating income')
    ocf=series(cf,'Operating cash flow'); fcf=series(cf,'Free cash flow')
    equity=number(bs,'Stockholders equity'); assets=number(bs,'Total assets')
    liabilities=number(bs,'Total liabilities'); cash=number(bs,'Cash and equivalents')
    ca=number(bs,'Current assets'); cl=number(bs,'Current liabilities')
    eps=number(inc,'Diluted EPS')
    roe=safe_div(net[0],equity) if net else None
    operating_margin=safe_div(op[0],rev[0]) if op and rev else None
    current_ratio=safe_div(ca,cl)
    liabilities_assets=safe_div(liabilities,assets)
    fcf_positive=(sum(x>0 for x in fcf),len(fcf)) if fcf else (0,0)
    earnings_positive=(sum(x>0 for x in net),len(net)) if net else (0,0)
    rev_growth=safe_div(rev[0]-rev[1],abs(rev[1])) if len(rev)>=2 else None
    quality=[
        metric_check('ROE > 15%',roe,roe>0.15 if roe is not None and equity>0 else None,'ROE can be inflated by leverage or buybacks.'),
        metric_check('Operating margin > 15%',operating_margin,operating_margin>0.15 if operating_margin is not None else None,'Sector-specific; compare with peers.'),
        metric_check('Positive earnings in >= 5 annual periods',f'{earnings_positive[0]}/{earnings_positive[1]}',earnings_positive[0]>=5 if earnings_positive[1]>=5 else None,'Requires five distinct annual periods.'),
        metric_check('Positive FCF in >= 5 annual periods',f'{fcf_positive[0]}/{fcf_positive[1]}',fcf_positive[0]>=5 if fcf_positive[1]>=5 else None,'Requires five distinct annual periods.'),
        metric_check('Liabilities / assets < 70%',liabilities_assets,liabilities_assets<0.7 if liabilities_assets is not None else None,'Not suitable as a universal bank/insurer criterion.'),
        metric_check('Positive latest revenue growth',rev_growth,rev_growth>0 if rev_growth is not None else None,'One-year change is not a durability test.'),
    ]
    graham=[
        metric_check('Positive earnings in >= 5 annual periods',f'{earnings_positive[0]}/{earnings_positive[1]}',earnings_positive[0]>=5 if earnings_positive[1]>=5 else None,'Graham historically favored longer records.'),
        metric_check('Current ratio >= 2',current_ratio,current_ratio>=2 if current_ratio is not None else None,'Industrial-company reference only.'),
        metric_check('Liabilities / assets < 50%',liabilities_assets,liabilities_assets<0.5 if liabilities_assets is not None else None,'Conservative proxy; not a Graham formula.'),
        metric_check('Positive stockholders equity',equity,equity>0 if equity is not None else None,'Negative equity makes book-based valuation inapplicable.'),
    ]
    def score(rows):
        eligible=[r for r in rows if r['Pass'] is not None]
        # Avoid giving a polished score when coverage is too sparse.
        return round(100*sum(r['Pass'] for r in eligible)/len(eligible)) if len(eligible)>=4 else None
    bvps=safe_div(equity,shares) if shares is not None and shares>0 else None
    graham_number=math.sqrt(22.5*eps*bvps) if eps is not None and eps>0 and bvps is not None and bvps>0 else None
    margin_of_safety=(graham_number-price)/graham_number if graham_number and price is not None and price>0 else None
    return {'quality_checks':pd.DataFrame(quality),'graham_checks':pd.DataFrame(graham),
            'quality_score':score(quality),'graham_evidence_score':score(graham),
            'roe':roe,'operating_margin':operating_margin,'current_ratio':current_ratio,
            'liabilities_assets':liabilities_assets,'revenue_growth':rev_growth,
            'graham_number':graham_number,'margin_of_safety':margin_of_safety,
            'eps':eps,'bvps':bvps,'cash':cash}
