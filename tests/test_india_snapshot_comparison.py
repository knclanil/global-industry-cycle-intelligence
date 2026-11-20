import pandas as pd
from fundamental_rankings_engine import get_rankings, snapshot_comparison


def test_india_snapshot_is_visible_and_explicitly_not_historical_rank():
    data = get_rankings('India')
    assert len(data) >= 500
    assert (data['Status'] != 'Ranked').all()
    comparison = snapshot_comparison(data)
    assert comparison['Snapshot comparison / 100'].notna().sum() >= 400
    assert comparison['Snapshot position'].notna().sum() >= 400
    assert comparison['Fundamental score'].isna().all()
    assert comparison['Rank'].isna().all()
