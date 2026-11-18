from pathlib import Path
from scripts.refresh_holdings import parse_document
from holdings_intelligence import normalize

FIXTURE = Path(__file__).parent / 'fixtures' / 'USMV_holdings.csv'

def test_real_ishares_csv_metadata_and_footer():
    frame, asof = parse_document(FIXTURE.read_bytes())
    assert asof == '2026-11-17'
    assert len(frame) == 179
    assert frame.iloc[0]['Ticker'] == 'BRK B'
    assert frame.iloc[0]['Weight (%)'] == '1.64'

def test_real_ishares_csv_equity_filter():
    frame, asof = parse_document(FIXTURE.read_bytes())
    result = normalize(frame, '239695', asof)
    assert len(result) == 174
    assert 99 < result.weight.sum() < 101

def test_missing_asof_rejected():
    blob = b'Ticker,Name,Weight (%)\nABC,Example Inc,2.0\n'
    try: parse_document(blob)
    except ValueError as exc: assert 'date' in str(exc).lower()
    else: raise AssertionError('Unverified date accepted')
