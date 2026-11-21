"""Detailed USA data quality & readiness diagnostics; no external calls."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/usa_research/company_research.csv'
REPORT=ROOT/'data/usa_research/completion_report.json'
MISSING=ROOT/'data/usa_research/financial_gaps.csv'

def present(df,name):
    if name not in df:return pd.Series(False,index=df.index)
    return pd.to_numeric(df[name],errors='coerce').notna()

def flag(df,name):
    if name not in df:return pd.Series(False,index=df.index)
    return df[name].astype(str).str.casefold().eq('yes')

def generate(df):
    base={k:present(df,k) for k in ('revenue','net_income','roe','operating_margin','operating_cash_flow','free_cash_flow','debt_to_equity','price','market_cap','pe','pb')}
    ready=flag(df,'fundamental_ready')
    valued=flag(df,'valuation_ready')
    joined=ready & valued
    scored=present(df,'research_score')
    report={'built_utc':datetime.now(timezone.utc).isoformat(),'universe':len(df),
       'fundamental_ready':int(ready.sum()),'valuation_ready':int(valued.sum()),
       'both_ready':int(joined.sum()),'research_ready':int(flag(df,'research_ready').sum()),
       'research_score_populated':int(scored.sum()),
       'fundamentals_without_valuation':int((ready&~valued).sum()),
       'valuation_without_fundamentals':int((valued&~ready).sum()),
       'metric_counts':{k:int(mask.sum()) for k,mask in base.items()},
       'note':'Research-ready means usable fundamental + valuation inputs, not a scored or recommended investment.'}
    cols=[c for c in ('company_key','ticker','company','financial_period','quote_asof','readiness_reason') if c in df]
    gaps=df[cols].copy()
    gaps['fundamental_ready']=ready.values
    gaps['valuation_ready']=valued.values
    gaps['research_ready']=joined.values
    gaps['missing_metrics']=[', '.join(k for k,mask in base.items() if not mask.iloc[i]) for i in range(len(df))]
    return report,gaps

if __name__=='__main__':
    if not DATA.exists():raise SystemExit(f'USA dataset not built: {DATA}')
    frame=pd.read_csv(DATA,low_memory=False)
    if 'company_key' not in frame or frame.company_key.isna().any() or frame.company_key.duplicated().any():
        raise SystemExit('Unusable issuer key: missing or duplicate USA company_key')
    report,gaps=generate(frame)
    REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    gaps.to_csv(MISSING,index=False)
    print(json.dumps(report,indent=2))
