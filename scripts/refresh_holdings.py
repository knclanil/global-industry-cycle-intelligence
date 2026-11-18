"""Fetch and validate BlackRock holdings; only commit complete verified snapshots."""
import io,sys,hashlib,re
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from holdings_intelligence import STORE,SOURCES,url_for,normalize,rank_companies


DATE_PATTERNS = (
    r"(?:Fund\s+Holdings\s+as\s+of|Holdings\s+as\s+of|As\s+of\s+Date|Holdings\s+Date|Data\s+as\s+of)\s*[:,-]?\s*[\"']?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})",
    r"(?:Fund\s+Holdings\s+as\s+of|Holdings\s+as\s+of)\s*[,\t]\s*[\"']?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4}-\d{2}-\d{2})",
)

def verified_date(text):
    """Only a date explicitly labeled as holdings-as-of in the document qualifies."""
    for pattern in DATE_PATTERNS:
        match=re.search(pattern,text,re.I)
        if match:
            date=pd.to_datetime(match.group(1),errors='coerce')
            if not pd.isna(date):return date.date().isoformat()
    return None

def has_holdings_columns(frame):
    cols={str(c).strip().lower().replace(' ','_') for c in frame.columns}
    return bool(cols & {'name','company','security_name','issuer_name'}) and bool(cols & {'weight_(%)','weight_%','weight_pct','weight','portfolio_weight','weightage'})

def parse_document(blob):
    """Read holdings AND source metadata, including the common iShares CSV preamble."""
    if blob[:2]==b'PK' or blob[:4]==b'\xd0\xcf\x11\xe0':
        book=pd.ExcelFile(io.BytesIO(blob))
        for sheet in book.sheet_names:
            raw=pd.read_excel(book,sheet_name=sheet,header=None,nrows=35)
            preamble='\n'.join(' '.join(str(v) for v in row if pd.notna(v)) for row in raw.values)
            asof=verified_date(preamble)
            for skip in range(0,25):
                try:
                    frame=pd.read_excel(book,sheet_name=sheet,skiprows=skip)
                    if has_holdings_columns(frame):return frame,asof
                except (ValueError,IndexError):pass
        raise ValueError('No recognized holdings table in workbook')
    text=blob.decode('utf-8-sig',errors='replace')
    if text.lstrip().startswith(('{','<','<!')):raise ValueError('Received JSON/HTML rather than a holdings spreadsheet')
    # iShares CSV metadata often has a date on the second line, e.g.
    # Fund Holdings as of,"Nov 17, 2026".  Parse before stripping metadata.
    asof=verified_date('\n'.join(text.splitlines()[:35]))
    for skip in range(0,35):
        for sep in (',','\t',';'):
            try:
                frame=pd.read_csv(io.StringIO(text),skiprows=skip,sep=sep,on_bad_lines='skip',low_memory=False)
                if has_holdings_columns(frame):return frame,asof
            except (ValueError,pd.errors.ParserError):pass
    raise ValueError('No recognized holdings table; inspect source format')

def refresh():
    STORE.mkdir(parents=True,exist_ok=True)
    session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; holdings-monitor/1.0)'})
    successes=[];failures=[]
    today=datetime.now(timezone.utc).strftime('%Y%m%d')
    for pid in SOURCES:
        try:
            response=session.get(url_for(pid,today),timeout=45);response.raise_for_status()
            if len(response.content)<100:raise ValueError('Empty or suspicious response')
            frame,document_asof=parse_document(response.content)
            date_cols=[c for c in frame.columns if str(c).lower().strip().replace(' ','_') in ('as_of','as_of_date','holdings_date')]
            asof=document_asof
            if not asof and date_cols:
                dates=pd.to_datetime(frame[date_cols[0]].dropna(),errors='coerce').dropna()
                if not dates.empty:asof=dates.iloc[0].date().isoformat()
            if not asof:
                raise ValueError('Actual holdings as-of date not verified; source format may require adapter')
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
