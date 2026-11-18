"""Safely ingest iShares holdings CSV/XLSX, retaining diagnostics on source failures.

Unverified or unavailable source data never becomes a zero holding or a removal.
A network/source failure is reported as a warning rather than failing the scheduled job.
"""
import csv
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from holdings_intelligence import STORE, SOURCES, url_for, normalize, rank_companies

# Adapted from the supplied Factor Holdings Intelligence collectors v1.8.1/v1.8.5.
# Their key insight: metadata may be embedded in one cell or spread across rows;
# headers vary, and issuer-declared effective date must be parsed independently.
HEADER_ALIASES = {
    'ticker': {'ticker','tickersymbol','symbol','securityticker','stockticker','holdingsticker'},
    'weight': {'weight','weightpct','weightpercent','weightpercentage','portfolioweight','weighting','weightofnetassets','percentofnetassets','netassetspercent','ofnetassets','marketweight','marketweightpct','marketweightpercent'},
    'name': {'name','securityname','description','securitydescription','companyname'},
}

def _norm(value):
    return re.sub(r'[^a-z0-9]', '', str(value).lower())

def _date(value):
    value = str(value).strip().strip('\"\'').strip()
    if not value: return None
    try:
        dt = pd.to_datetime(value, errors='raise')
        return dt.date().isoformat() if pd.notna(dt) else None
    except (ValueError, TypeError, OverflowError):
        return None

DATE_PATTERNS = [
    re.compile(r'(?:fund\s+)?holdings\s+as\s+of\s*[,;:\t\" ]+\s*([0-9]{1,2}[-/][A-Za-z]{3,9}[-/][0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{2,4}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', re.I),
    re.compile(r'(?:fund\s+)?holdings\s*[,;:\t\" ]+\s*([0-9]{1,2}[-/][A-Za-z]{3,9}[-/][0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', re.I),
    re.compile(r'(?:effective\s+date|portfolio\s+date|holdings\s+date|data\s+as\s+of|as\s+of\s+date)\s*[,;:\t\" ]+\s*([0-9]{1,2}[-/][A-Za-z]{3,9}[-/][0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{1,2},?\s+[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', re.I),
]

def _metadata_date(rows):
    for row in rows:
        cells = [str(v).strip() for v in row]
        for i, cell in enumerate(cells):
            if _norm(cell) in {'fundholdingsasof','holdingsasof','asofdate','holdingsdate','dataasof','effectivedate','portfoliodate'}:
                for next_cell in cells[i+1:i+3]:
                    result = _date(next_cell)
                    if result: return result
        joined = ' '.join(c for c in cells if c)
        for pattern in DATE_PATTERNS:
            match = pattern.search(joined)
            if match:
                result = _date(match.group(1))
                if result: return result
    return None

def _header_index(rows):
    for i, row in enumerate(rows[:160]):
        fields = {_norm(c) for c in row}
        if fields & HEADER_ALIASES['ticker'] and fields & HEADER_ALIASES['weight'] and fields & HEADER_ALIASES['name']:
            return i
    return None

def _rows_to_frame(rows):
    idx = _header_index(rows)
    if idx is None: raise ValueError('No recognized holdings table (ticker/name/weight)')
    asof = _metadata_date(rows[:idx])
    if not asof: raise ValueError('Holdings table recognized, but issuer-declared holdings-as-of date missing')
    raw_header = [str(c).strip() for c in rows[idx]]
    header = []
    for c in raw_header:
        key = _norm(c)
        if key in HEADER_ALIASES['ticker']: c = 'Ticker'
        elif key in HEADER_ALIASES['name']: c = 'Name'
        elif key in HEADER_ALIASES['weight']: c = 'Weight (%)'
        header.append(c)
    if len(header) != len(set(header)):
        raise ValueError('Ambiguous duplicate normalized header columns')
    records = []
    for row in rows[idx+1:]:
        if len(row) != len(header):
            if records: break
            continue
        item = dict(zip(header,row))
        if not str(item.get('Name','')).strip() or not str(item.get('Weight (%)','')).strip():
            if records: break
            continue
        records.append(item)
    if not records: raise ValueError('No holdings records after recognized header')
    return pd.DataFrame.from_records(records), asof

def _parse_csv(blob):
    if blob.startswith((b'\xff\xfe',b'\xfe\xff')): text=blob.decode('utf-16')
    else:
        try: text=blob.decode('utf-8-sig')
        except UnicodeDecodeError: text=blob.decode('cp1252')
    if text.lstrip().lower().startswith(('{','<','<!')):
        raise ValueError('Source returned JSON or HTML, not holdings CSV')
    for delimiter in (',','\t',';'):
        rows = list(csv.reader(io.StringIO(text,newline=''),delimiter=delimiter))
        if _header_index(rows) is not None: return _rows_to_frame(rows)
    raise ValueError('No recognized iShares CSV holdings header')

def _parse_excel(blob):
    book=pd.ExcelFile(io.BytesIO(blob))
    for sheet in book.sheet_names:
        raw=pd.read_excel(book,sheet_name=sheet,header=None,dtype=str,keep_default_na=False)
        rows=raw.fillna('').values.tolist()
        if _header_index(rows) is not None: return _rows_to_frame(rows)
    raise ValueError('No recognized holdings header in Excel workbook')

def parse_document(blob):
    if blob[:2]==b'PK' or blob[:4]==b'\xd0\xcf\x11\xe0': return _parse_excel(blob)
    return _parse_csv(blob)

def _safe_diagnostic(pid, response=None, error=None):
    path = STORE / 'diagnostics'
    path.mkdir(parents=True, exist_ok=True)
    details = {'portfolio_id': str(pid), 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
               'error': str(error)[:350] if error else ''}
    if response is not None:
        details.update(status_code=response.status_code, content_type=response.headers.get('Content-Type', ''),
                       content_disposition=response.headers.get('Content-Disposition', ''),
                       content_length=len(response.content),
                       body_sha256=hashlib.sha256(response.content).hexdigest(),
                       detected_magic=response.content[:8].hex())
        # Diagnostic metadata only: never publish constituent rows or raw documents.
        try:
            body=response.content
            decoded=body.decode('utf-16' if body.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
            lines=decoded.splitlines()[:12]
            details['metadata_labels']=[re.sub(r'[^a-zA-Z ]','',line.split(',')[0])[:65] for line in lines if line.strip()][:10]
        except Exception: pass
    # Never upload raw HTML response, URL query strings or response cookies.
    (path / f'{pid}.json').write_text(json.dumps(details, indent=2), encoding='utf-8')

def _candidate_dates(now=None):
    """Try an explicit date first, then previous weekdays (no fabricated as-of dates)."""
    now = now or datetime.now(timezone.utc)
    override = os.environ.get('HOLDINGS_ASOF_DATE', '').strip()
    if override:
        try:
            start = datetime.strptime(override, '%Y%m%d').date()
        except ValueError as exc:
            raise ValueError('HOLDINGS_ASOF_DATE must be YYYYMMDD') from exc
        if start > now.date():
            raise ValueError('HOLDINGS_ASOF_DATE cannot be in the future')
    else:
        # Holdings are typically published after the trading day closes.
        start = now.date() - timedelta(days=1)
    lookback = int(os.environ.get('HOLDINGS_LOOKBACK_DAYS', '10'))
    if not 1 <= lookback <= 30:
        raise ValueError('HOLDINGS_LOOKBACK_DAYS must be between 1 and 30')
    return [(start - timedelta(days=i)).strftime('%Y%m%d')
            for i in range(lookback) if (start - timedelta(days=i)).weekday() < 5]


def _fetch_verified(session, pid, dates):
    """Accept only source-dated, parseable, nontrivial holdings."""
    attempts = []
    last_response = None
    for requested in dates:
        try:
            response = session.get(url_for(pid, requested), timeout=45)
            last_response = response
            response.raise_for_status()
            if len(response.content) < 100:
                raise ValueError('Empty or suspiciously short response')
            frame, asof = parse_document(response.content)
            if asof > requested[:4] + '-' + requested[4:6] + '-' + requested[6:]:
                raise ValueError('Issuer date is later than requested date')
            if asof > datetime.now(timezone.utc).date().isoformat():
                raise ValueError('Issuer date is in the future')
            # A valid date alone is not enough: prevent a 2-row partial document.
            if len(frame) < 10:
                raise ValueError(f'Only {len(frame)} holding rows; incomplete document')
            return frame, asof, requested, attempts
        except (requests.RequestException, ValueError, UnicodeError, KeyError) as exc:
            attempts.append({'requested_date': requested, 'error': str(exc)[:180],
                             'status_code': last_response.status_code if last_response is not None else None})
    message = '; '.join(f"{a['requested_date']}: {a['error']}" for a in attempts)
    err = ValueError('No verified holdings document across requested dates: ' + message[:700])
    err.attempts = attempts
    err.last_response = last_response
    raise err


def refresh():
    STORE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*'})
    successes, failures = [], []
    dates = _candidate_dates()
    pending_path = STORE / 'pending_sources.json'
    pending = json.loads(pending_path.read_text()).get('portfolio_ids', []) if pending_path.exists() else []
    all_sources = list(dict.fromkeys([*SOURCES, *pending]))
    for pid in all_sources:
        try:
            frame, asof, requested, attempts = _fetch_verified(session, pid, dates)
            if pid in SOURCES:
                df = normalize(frame, pid, asof)
                if len(df) < 10 or not 80 <= float(df.weight.sum()) <= 105:
                    raise ValueError(f'Equity holdings validation failed: {len(df)} equities, {df.weight.sum():.2f}% total weight')
                successes.append(df)
                print(f'{pid}: verified {len(df)} equity holdings as of {asof} (requested {requested})', flush=True)
            else:
                print(f'{pid}: parsed {len(frame)} rows as of {asof}; category pending, excluded from rankings', flush=True)
            (STORE / 'diagnostics' / f'{pid}.json').unlink(missing_ok=True)
        except Exception as exc:
            failures.append(f'{pid}: {exc}')
            response = getattr(exc, 'last_response', None)
            _safe_diagnostic(pid, response, exc)
            diagnostic = STORE / 'diagnostics' / f'{pid}.json'
            details = json.loads(diagnostic.read_text())
            details['attempts'] = getattr(exc, 'attempts', [])
            diagnostic.write_text(json.dumps(details, indent=2), encoding='utf-8')
    for msg in failures: print('WARNING', msg, file=sys.stderr)
    if not successes:
        print('No verified active ETF sources; rankings preserved.', file=sys.stderr)
        return 1 if os.environ.get('HOLDINGS_STRICT') == '1' else 0
    if failures:
        print(f'PROVISIONAL ranking: {len(successes)}/{len(SOURCES)} active ETFs verified; missing ETFs are not removals.', file=sys.stderr)
    current = pd.concat(successes, ignore_index=True)
    prior_file = STORE / 'latest_holdings.parquet'
    previous = pd.read_parquet(prior_file) if prior_file.exists() else None
    if previous is not None:
        previous = previous[previous.portfolio_id.isin(current.portfolio_id.unique())].copy()
    if previous is not None:
        keys = ['portfolio_id', 'issuer_id']
        a = current.sort_values(keys).reset_index(drop=True)
        b = previous.sort_values(keys).reset_index(drop=True)
        if a.equals(b):
            print('No new verified holdings changes')
            return 0
    ranking, changes = rank_companies(current, previous)
    # Existing ETFs may have the same issuer date; only compare genuinely newer snapshots.
    # Missing ETFs are excluded above, never treated as removed.
    coverage = {'verified_active_etfs': sorted(current.portfolio_id.unique().tolist()),
                'verified_count': int(current.portfolio_id.nunique()),
                'expected_active_count': len(SOURCES),
                'pending_count': len(pending),
                'holdings_dates': sorted(current.as_of.unique().tolist()),
                'ranking_status': 'complete' if current.portfolio_id.nunique() == len(SOURCES) else 'provisional'}
    (STORE / 'coverage.json').write_text(json.dumps(coverage, indent=2), encoding='utf-8')
    datekey = max(current.as_of)
    fingerprint = hashlib.sha256(pd.util.hash_pandas_object(current, index=False).values.tobytes()).hexdigest()[:12]
    snapshot = STORE / 'snapshots' / f'{datekey}-{fingerprint}.parquet'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    current.to_parquet(snapshot, index=False)
    old_saved = pd.read_parquet(prior_file) if prior_file.exists() else None
    persisted = current if old_saved is None else pd.concat([current, old_saved[~old_saved.portfolio_id.isin(current.portfolio_id.unique())]], ignore_index=True)
    persisted.to_parquet(prior_file, index=False)
    ranking.to_parquet(STORE / 'company_rankings.parquet', index=False)
    if changes.empty:
        changes = pd.DataFrame(columns=['portfolio_id', 'issuer_id', 'company', 'event', 'previous_weight', 'current_weight', 'previous_as_of', 'current_as_of', 'points'])
    changes.to_parquet(STORE / 'latest_changes.parquet', index=False)
    history = STORE / 'holding_events.parquet'
    if history.exists():
        changes = pd.concat([pd.read_parquet(history), changes], ignore_index=True).drop_duplicates()
    changes.to_parquet(history, index=False)
    print(f'Saved {len(ranking)} company rankings')
    return 0

if __name__ == '__main__':
    sys.exit(refresh())
