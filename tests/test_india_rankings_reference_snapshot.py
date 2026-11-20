import pandas as pd
from fundamental_rankings_engine import load_india_reference_snapshot, rank_fundamentals

def test_reference_snapshot_is_visible_but_not_rankable():
    snapshot = load_india_reference_snapshot()
    assert len(snapshot) >= 500
    assert snapshot['Ticker'].eq('360ONE').any()
    assert snapshot['ROE'].notna().any()
    assert (snapshot['Years'] == 0).all()
    result = rank_fundamentals(snapshot)
    assert result['Fundamental score'].isna().all()
    assert result['Rank'].isna().all()
    assert result['Status'].str.contains('Insufficient').all()
