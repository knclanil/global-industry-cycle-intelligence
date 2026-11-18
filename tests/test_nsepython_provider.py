import sys
import types
import unittest
from unittest.mock import patch
from datetime import date
import pandas as pd
import nsepython_provider as provider

class NSEPythonProviderTests(unittest.TestCase):
    def test_normalize(self):
        raw = pd.DataFrame({'HistoricalDate':['01-Nov-2024','04-Nov-2024'], 'OPEN':['100','101'], 'HIGH':['102','103'], 'LOW':['99','100'], 'CLOSE':['101','102']})
        frame = provider.normalize_index_history(raw, 'NIFTY 50')
        self.assertEqual(frame['Adj Close'].iloc[-1], 102)
        self.assertEqual(len(frame), 2)

    def test_conflicting_duplicate_rejected(self):
        raw = pd.DataFrame({'HistoricalDate':['01-Nov-2024','01-Nov-2024'], 'OPEN':[100,101], 'HIGH':[102,103], 'LOW':[99,100], 'CLOSE':[101,102]})
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            provider.normalize_index_history(raw, 'NIFTY 50')

    def test_wrapper_call_and_dates(self):
        raw = pd.DataFrame({'HistoricalDate':['01-Nov-2024','04-Nov-2024'], 'OPEN':[100,101], 'HIGH':[102,103], 'LOW':[99,100], 'CLOSE':[101,102]})
        calls=[]
        def fake(name, start, end):
            calls.append((name,start,end));return raw
        with patch.dict(sys.modules, {'nsepythonserver': types.SimpleNamespace(index_history=fake)}):
            result=provider.history('NIFTY 50',date(2024,11,1),date(2024,11,4))
        self.assertEqual(calls,[('NIFTY 50','01-Nov-2024','04-Nov-2024')])
        self.assertEqual(result.attrs['source'],'NSEPythonServer (Nifty Indices)')

if __name__=='__main__': unittest.main()
