from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.refresh_holdings import _candidate_dates, _fetch_verified

FIXTURE = Path(__file__).parent / 'fixtures' / 'USMV_holdings.csv'


def test_previous_weekday_is_first(monkeypatch):
    monkeypatch.delenv('HOLDINGS_ASOF_DATE', raising=False)
    dates = _candidate_dates(datetime(2026, 11, 18, tzinfo=timezone.utc))
    assert dates[:2] == ['20261117', '20261116']


def test_explicit_date(monkeypatch):
    monkeypatch.setenv('HOLDINGS_ASOF_DATE', '20261117')
    assert _candidate_dates(datetime(2026, 11, 18, tzinfo=timezone.utc))[0] == '20261117'


def test_fallback_rejects_placeholder_then_accepts_verified():
    placeholder = b'iShares ETF\nFund Holdings as of,"-"\n\nTicker,Name,Weight (%)\nABC,Example,1.0\n'
    responses = []
    for blob in (placeholder, FIXTURE.read_bytes()):
        response = Mock(content=blob, status_code=200)
        response.raise_for_status.return_value = None
        responses.append(response)
    session = Mock()
    session.get.side_effect = responses
    frame, asof, requested, attempts = _fetch_verified(session, '239695', ['20261118', '20261117'])
    assert len(frame) == 179
    assert asof == '2026-11-17'
    assert requested == '20261117'
    assert len(attempts) == 1


def test_no_valid_document_fails_closed():
    response = Mock(content=b'Fund Holdings as of,"-"\nTicker,Name,Weight (%)\n', status_code=200)
    response.raise_for_status.return_value = None
    session = Mock()
    session.get.return_value = response
    with pytest.raises(ValueError, match='No verified holdings'):
        _fetch_verified(session, '239695', ['20261117'])
