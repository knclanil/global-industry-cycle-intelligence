from datetime import date
import pandas as pd
from india_asset_recovery import normalise_quote, recover, coverage

def sample(n=120):
    return pd.DataFrame({'Close':[100+i for i in range(n)],'Volume':[1000]*n},
        index=pd.date_range('2026-04-01', periods=n, freq='B'))

def test_clean_and_detect_short():
    f = normalise_quote(sample(), 'mock')
    assert len(f) == 120 and {'Adj Close','Volume'}.issubset(f.columns)
    assert coverage({'NIFTYBEES.NS':f}, date(2026,11,21), 63).shape[0] == 6

def test_no_fabricated_rows(monkeypatch):
    import india_asset_recovery as m
    monkeypatch.setattr(m, 'download_one', lambda *a, **k: pd.DataFrame())
    frames = recover(lambda *a: {}, date(2026,1,1), date(2026,11,21))
    assert frames == {}
