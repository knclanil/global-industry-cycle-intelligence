"""Fetch and validate BlackRock holdings; only commit complete verified snapshots."""
import io,sys,hashlib,re
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from holdings_intelligence import STORE,SOURCES,url_for,normalize,rank_companies


def parse_document(blob):
    if blob[:2]==b'PK':return pd.read_excel(io.BytesIO(blob))
    if blob[:4]==b'\xd0\xcf\x11\xe0':return pd.read_excel(io.BytesIO(blob))
    text=blob.decode('utf-8-sig')
    if text.lstrip().startswith(('{','<','<!')):raise ValueError('Received API response/HTML, not holdings spreadsheet')
    for skip in range(0,12):
        for sep in (',','\t',';'):
            try:
                df=pd.read_csv(io.StringIO(text),skiprows=skip,sep=sep,on_bad_lines='skip')
                if any('weight' in str(c).lower() for c in df.columns):return df
            except (ValueError,pd.errors.ParserError):pass
    raise ValueError('No recognized holdings table')

def refresh():
    STORE.mkdir(parents=True,exist_ok=True)
    session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; holdings-monitor/1.0)'})
    successes=[];failures=[]
    today=datetime.now(timezone.utc).strftime('%Y%m%d')
    for pid in SOURCES:
        try:
            response=session.get(url_for(pid,today),timeout=45);response.raise_for_status()
            if len(response.content)<100:raise ValueError('Empty or suspicious response')
            frame=parse_document(response.content)
            # Do not assert request date is actual holdings date. Prefer a verified date
            # field; otherwise reject to avoid generating false daily change events.
            date_cols=[c for c in frame.columns if str(c).lower().replace(' ','_') in ('as_of','as_of_date','holdings_date')]
            if date_cols:
                asof=pd.to_datetime(frame[date_cols[0]].dropna().iloc[0]).date().isoformat()
            else:
                # Many iShares CSV files carry the holdings date in the preamble.
                header=response.content[:2500].decode('utf-8-sig',errors='replace')
                match=re.search(r'(?:Fund Holdings as of|Holdings as of|As of Date)[^\r\n]{0,60}?(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})',header,re.I)
                if not match:raise ValueError('Actual holdings as-of date not verified in source; needs source-specific parser')
                asof=pd.to_datetime(match.group(1)).date().isoformat()
            df=normalize(frame,pid,asof)
            successes.append(df)
            print(f'{pid}: validated {len(df)} holdings as of {asof}')
        except Exception as exc:
            failures.append(f'{pid}: {exc}')
    for error in failures:print('WARNING',error,file=sys.stderr)
    # Atomic universe rule: no removal inference from failed/unavailable ETF sources.
    if failures:
        print(f'No rankings written: {len(failures)} of {len(SOURCES)} sources failed verification',file=sys.stderr)
        return 1
    current=pd.concat(successes,ignore_index=True)
    prior_file=STORE/'latest_holdings.parquet'
    previous=pd.read_parquet(prior_file) if prior_file.exists() else None
    if previous is not None and current.sort_values(['portfolio_id','issuer_id']).reset_index(drop=True).equals(previous.sort_values(['portfolio_id','issuer_id']).reset_index(drop=True)):
        print('No holdings changes');return 0
    # Compare only the most recent snapshots; adjustment is not cumulative.
    ranking,changes=rank_companies(current,previous)
    datekey=max(current.as_of)
    snapshot=STORE/'snapshots'/f'{datekey}-{hashlib.sha256(pd.util.hash_pandas_object(current,index=False).values.tobytes()).hexdigest()[:12]}.parquet'
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    current.to_parquet(snapshot,index=False)
    current.to_parquet(prior_file,index=False)
    ranking.to_parquet(STORE/'company_rankings.parquet',index=False)
    if changes.empty:
        changes=pd.DataFrame(columns=['portfolio_id','issuer_id','company','event','previous_weight','current_weight','previous_as_of','current_as_of','points'])
    changes.to_parquet(STORE/'latest_changes.parquet',index=False)
    history=STORE/'holding_events.parquet'
    if history.exists():changes=pd.concat([pd.read_parquet(history),changes],ignore_index=True).drop_duplicates()
    changes.to_parquet(history,index=False)
    print(f'Saved {len(ranking)} company rankings and verified change events');return 0

if __name__=='__main__':sys.exit(refresh())
