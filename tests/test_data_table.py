from datetime import date
import pandas as pd
from data_table import raw_rows, coverage
import india_factor_market_data as factors

def test_raw_rows_preserves_duplicates_and_flags_bad_prices():
    dates = pd.to_datetime(['2026-01-05','2026-01-05','2026-01-06'])
    frame = pd.DataFrame({'Open':[10,10,0],'High':[11,11,1],'Low':[9,9,1],'Close':[10,10,1],'Adj Close':[10,10,0],'Volume':[5,5,0]}, index=dates)
    frame.attrs['source'] = 'Test NSE'
    result = raw_rows({'TEST':frame})
    assert len(result)==3
    assert result['Row duplicate'].sum()==2
    assert result['Invalid price'].sum()==1
    assert set(result['Source'])=={'Test NSE'}

def test_missing_indices_reported():
    summary = coverage({}, factors, date(2026,1,1), date(2026,1,31))
    assert len(summary)==len(factors.SECTORS)+1
    assert (summary['Status']=='MISSING').all()

def test_date_filter():
    frame=pd.DataFrame({'Adj Close':[10,11]},index=pd.to_datetime(['2026-01-05','2026-02-05']))
    result=raw_rows({'X':frame},start=date(2026,2,1),end=date(2026,2,28))
    assert len(result)==1
