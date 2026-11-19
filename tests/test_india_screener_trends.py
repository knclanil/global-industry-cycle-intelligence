import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from india_screener_trends import series_from, pct_ratio, growth_pct

def test_chronological_periods():
    frame = pd.DataFrame({'Particulars':['Sales +'], 'Mar 2025':['150'], 'Mar 2023':['100'], 'Mar 2024':['120']})
    out = series_from(frame,'Revenue')
    assert list(out.index) == ['Mar 2023','Mar 2024','Mar 2025']

def test_quarterly_year_over_year_requires_comparable_periods():
    s = pd.Series({'Jun 2025':140, 'Jun 2024':100, 'Dec 2024':150})
    out = growth_pct(s,4)
    assert len(out)==1 and abs(out.loc['Jun 2025']-40)<1e-8

def test_qoq_missing_quarter_not_filled():
    s = pd.Series({'Mar 2025':100, 'Sep 2025':150})
    assert growth_pct(s,1).empty

def test_zero_denominator_is_missing():
    a = pd.Series({'Mar 2025':20}); b=pd.Series({'Mar 2025':0})
    assert pct_ratio(a,b).empty

def test_quarterly_does_not_use_ttm():
    f=pd.DataFrame({'Particulars':['Sales +'], 'Jun 2025':['25'], 'TTM':['100']})
    assert list(series_from(f,'Revenue',frequency='Quarterly').index)==['Jun 2025']
