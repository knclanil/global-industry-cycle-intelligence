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
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from holdings_intelligence import STORE, SOURCES, url_for, normalize, rank_companies

HEADER_FIELDS = {'ticker', 'name', 'sector', 'asset class', 'weight (%)'}
DATE_LABEL = re.compile(r'^(?:fund\s+)?holdings\s+as\s+of$|^as\s+of\s+date$|^holdings\s+date$|^data\s+as\s+of$', re.I)

def _date(value):
    value = str(value).strip().strip('"\'').strip()
    try:
        dt = pd.to_datetime(value, errors='raise')
        if pd.isna(dt): return None
        return dt.date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None

def _metadata_date(rows):
    for row in rows:
        cells = [str(c).strip().strip('"') for c in row]
        if len(cells) >= 2 and DATE_LABEL.fullmatch(cells[0]):
            result = _date(cells[1])
            if result: return result
        # Some exports combine the label and date into one cell.
        if cells:
            match = re.match(r'^(?:Fund\s+)?Holdings\s+as\s+of\s*[:\-]\s*(.+)$', cells[0], re.I)
            if match:
                result = _date(match.group(1))
                if result: return result
    return None

def _header_index(rows):
    for i, row in enumerate(rows):
        fields = {str(c).strip().lower().replace('\ufeff', '') for c in row}
        if {'name', 'weight (%)'}.issubset(fields) and ('ticker' in fields or 'isin' in fields):
            return i
    return None

def _parse_csv(blob):
    text = blob.decode('utf-8-sig')
    if text.lstrip().startswith(('{', '<', '<!')):
        raise ValueError('Source returned JSON or HTML, not holdings CSV')
    # csv.reader respects quoted commas in the metadata, securities and disclaimer.
    for delimiter in (',', '\t', ';'):
        try:
            rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=delimiter))
        except csv.Error:
            continue
        idx = _header_index(rows[:100])
        if idx is None: continue
        asof = _metadata_date(rows[:idx])
        if not asof:
            raise ValueError('Holdings table recognized, but document holdings-as-of date missing')
        header = [c.strip() for c in rows[idx]]
        records = []
        for row in rows[idx + 1:]:
            # BlackRock's long copyright disclaimer is often a quoted multiline CSV cell.
            if len(row) != len(header):
                if records: break
                continue
            item = dict(zip(header, row))
            if not item.get('Name', '').strip() or not item.get('Weight (%)', '').strip():
                if records: break
                continue
            records.append(item)
        if not records: raise ValueError('Recognized CSV header but no holdings records')
        return pd.DataFrame.from_records(records), asof
    raise ValueError('No recognized iShares CSV holdings header')

def _parse_excel(blob):
    book = pd.ExcelFile(io.BytesIO(blob))
    for sheet in book.sheet_names:
        raw = pd.read_excel(book, sheet_name=sheet, header=None, dtype=str)
        rows = raw.fillna('').values.tolist()
        idx = _header_index(rows[:100])
        if idx is None: continue
        asof = _metadata_date(rows[:idx])
        if not asof: raise ValueError('Excel holdings table recognized, but as-of date missing')
        header = [str(c).strip() for c in rows[idx]]
        frame = pd.DataFrame(rows[idx + 1:], columns=header)
        frame = frame[frame.get('Name', pd.Series(dtype=str)).astype(str).str.strip().ne('')]
        return frame, asof
    raise ValueError('No recognized holdings header in Excel workbook')

def parse_document(blob):
    if blob[:2] == b'PK' or blob[:4] == b'\xd0\xcf\x11\xe0':
        return _parse_excel(blob)
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
    # Never upload raw HTML response, URL query strings or response cookies.
    (path / f'{pid}.json').write_text(json.dumps(details, indent=2), encoding='utf-8')

def refresh():
    STORE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': 'text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*'})
    successes, failures = [], []
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    for pid in SOURCES:
        response = None
        try:
            response = session.get(url_for(pid, today), timeout=45)
            response.raise_for_status()
            if len(response.content) < 100: raise ValueError('Empty or suspiciously short response')
            frame, asof = parse_document(response.content)
            df = normalize(frame, pid, asof)
            successes.append(df)
            print(f'{pid}: verified {len(df)} equity holdings as of {asof}', flush=True)
            (STORE / 'diagnostics' / f'{pid}.json').unlink(missing_ok=True)
        except Exception as exc:
            failures.append(f'{pid}: {exc}')
            _safe_diagnostic(pid, response, exc)
    for msg in failures: print('WARNING', msg, file=sys.stderr)
    if failures:
        print(f'SKIPPED ranking update: {len(failures)} of {len(SOURCES)} sources unavailable or unverified. '
              'Prior verified rankings are preserved; no removals inferred. See data/holdings/diagnostics.', file=sys.stderr)
        # A scheduled fetch should not be marked failed for upstream data issues.
        # CI can opt into strict mode for debugging.
        return 1 if os.environ.get('HOLDINGS_STRICT') == '1' else 0
    current = pd.concat(successes, ignore_index=True)
    prior_file = STORE / 'latest_holdings.parquet'
    previous = pd.read_parquet(prior_file) if prior_file.exists() else None
    if previous is not None:
        keys = ['portfolio_id', 'issuer_id']
        a = current.sort_values(keys).reset_index(drop=True)
        b = previous.sort_values(keys).reset_index(drop=True)
        if a.equals(b):
            print('No new verified holdings changes')
            return 0
    ranking, changes = rank_companies(current, previous)
    datekey = max(current.as_of)
    fingerprint = hashlib.sha256(pd.util.hash_pandas_object(current, index=False).values.tobytes()).hexdigest()[:12]
    snapshot = STORE / 'snapshots' / f'{datekey}-{fingerprint}.parquet'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    current.to_parquet(snapshot, index=False)
    current.to_parquet(prior_file, index=False)
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
