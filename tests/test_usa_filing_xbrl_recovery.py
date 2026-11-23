import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from usa_filing_xbrl_recovery import parse_ixbrl,merge_into_companyfacts,choose_filing
HTML=b'''<html><body><xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="x">123</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context><xbrli:context id="seg"><xbrli:entity><xbrli:segment>segment</xbrli:segment></xbrli:entity><xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context><xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit><ix:nonFraction name="us-gaap:OperatingIncomeLoss" contextRef="c1" unitRef="usd" scale="6">2.5</ix:nonFraction><ix:nonFraction name="custom:OperatingIncomeLoss" contextRef="c1" unitRef="usd" scale="6">9</ix:nonFraction><ix:nonFraction name="us-gaap:OperatingIncomeLoss" contextRef="seg" unitRef="usd" scale="6">8</ix:nonFraction></body></html>'''
class RecoveryTests(unittest.TestCase):
 def test_whitelisted_and_consolidated(self):
  facts,rejected=parse_ixbrl(HTML,'0000000000-25-000001','https://www.sec.gov/filing')
  self.assertEqual(len(facts['OperatingIncomeLoss']['USD']),1)
  self.assertEqual(facts['OperatingIncomeLoss']['USD'][0]['val'],2500000)
  self.assertGreaterEqual(rejected,1)
 def test_custom_requires_explicit_mapping(self):
  facts,_=parse_ixbrl(HTML,'0000000000-25-000001','https://www.sec.gov/filing',{'custom:OperatingIncomeLoss':'OperatingIncomeLoss'})
  self.assertEqual(len(facts['OperatingIncomeLoss']['USD']),2)
 def test_merge_deduplicates(self):
  filing={'facts':{'OperatingIncomeLoss':{'USD':[{'accn':'a','end':'2025-12-31','val':10}]}}}
  a=merge_into_companyfacts({},filing)
  b=merge_into_companyfacts(a,filing)
  self.assertEqual(len(b['facts']['us-gaap']['OperatingIncomeLoss']['units']['USD']),1)
 def test_recent_filing(self):
  sub={'filings':{'recent':{'form':['8-K','10-K'],'accessionNumber':['a','0000000000-25-000001'],'primaryDocument':['x.htm','report.htm'],'filingDate':['2025-10-01','2026-02-01']}}}
  self.assertEqual(choose_filing(sub)[2],'report.htm')
if __name__=='__main__':unittest.main()
