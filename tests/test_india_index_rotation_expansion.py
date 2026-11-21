import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from india_index_rotation_expansion import (
    EXTRA_INDIA_INDICES, SOURCE_TICKERS, calculate_signal, build_extra_signals,
)


def test_all_thirteen_sources_classified():
    assert len(EXTRA_INDIA_INDICES) == 13
    assert len(SOURCE_TICKERS) == 13
    assert sum(x.kind == 'sector' for x in EXTRA_INDIA_INDICES) == 3
    assert sum(x.kind == 'factor' for x in EXTRA_INDIA_INDICES) == 10


def test_signal_must_have_sufficient_history():
    idx = pd.date_range('2025-01-01', periods=15, freq='B')
    series = pd.Series([100 + i for i in range(len(idx))], index=idx)
    result, reason = calculate_signal(series, series, 21)
    assert result is None
    assert 'Insufficient' in reason


def test_valid_signal_classifies_without_fabricating():
    idx = pd.date_range('2025-01-01', periods=300, freq='B')
    bench = pd.Series([100.0] * 300, index=idx)
    source = pd.Series([100 + i * i / 1000 for i in range(300)], index=idx)
    result, error = calculate_signal(source, bench, 63)
    assert not error
    assert result['quadrant'] in {'Leading', 'Improving', 'Weakening', 'Lagging'}


def test_build_reports_failing_provider_not_fake_signal():
    idx = pd.date_range('2025-01-01', periods=300, freq='B')
    bench = pd.DataFrame({'Adj Close': [100.0] * 300}, index=idx)
    def failure(_name, **_kwargs):
        raise RuntimeError('blocked')
    signals, status = build_extra_signals(bench, [21], fetcher=failure)
    assert signals[21].empty
    assert len(status) == 13
    assert (status.status == 'unavailable').all()
