import unittest
import pandas as pd
from india_research_data import membership_match, filter_companies, format_summary
from scripts.install_india_research_pages import patch

class ResearchPagesTests(unittest.TestCase):
    def setUp(self):
        self.df=pd.DataFrame([
            dict(company_key='A',company='Alpha',ticker='ALPHA',isin='IN1',sectors='Banking | Financial Services',
                 factors='Quality | Value',source_indices='Nifty Quality | Nifty Value',
                 fundamental_ready='Yes',valuation_ready='Yes',research_score=81,
                 industry='Financials',factor_count=2,sector_count=2,roe=.14,revenue_yoy=.12,
                 pe=13,pb=2,quality_score=70,growth_score=80,valuation_score=90,readiness_reason=''),
            dict(company_key='B',company='Beta',ticker='BETA',isin='IN2',sectors='Banking',factors='Growth',
                 source_indices='Nifty Growth',fundamental_ready='No',valuation_ready='No',
                 research_score=float('nan'),industry='Financials',factor_count=1,sector_count=1,
                 roe=None,revenue_yoy=None,pe=None,pb=None,quality_score=None,growth_score=None,
                 valuation_score=None,readiness_reason='Missing statements')])

    def test_multiple_factors_all_requires_each(self):
        self.assertTrue(membership_match('Quality | Value',['Quality','Value'],'ALL'))
        self.assertFalse(membership_match('Growth | Value',['Quality','Value'],'ALL'))

    def test_multiple_factors_any(self):
        found=filter_companies(self.df,factors=['Growth','Value'],match='ANY')
        self.assertEqual(set(found.ticker),{'ALPHA','BETA'})

    def test_filters_between_categories_are_and(self):
        found=filter_companies(self.df,sectors=['Banking'],factors=['Quality','Value'],match='ALL')
        self.assertEqual(list(found.ticker),['ALPHA'])

    def test_scored_gate_does_not_invent_scores(self):
        found=filter_companies(self.df,scored=True)
        self.assertEqual(list(found.ticker),['ALPHA'])

    def test_display_does_not_mutate_source(self):
        shown=format_summary(self.df)
        self.assertAlmostEqual(shown.loc[0,'ROE %'],14)
        self.assertEqual(self.df.loc[0,'roe'],.14)

    def test_installer_is_idempotent(self):
        from pathlib import Path
        base=(Path(__file__).resolve().parents[1]/'app.py').read_text()
        self.assertEqual(patch(base),base)

if __name__=='__main__':unittest.main()
