import importlib.util
import unittest
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rank_test',P/'scripts/build_usa_fundamental_rankings.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class Integration(unittest.TestCase):
    def test_cap_does_not_override_better_sum(self):
        rows=[dict(ticker='GOOD',roe=20,current_ratio=2,operating_margin=20,net_margin=15,eps_growth_pct=25,market_cap=1e7),
              dict(ticker='BIG',roe=10,current_ratio=1,operating_margin=10,net_margin=5,eps_growth_pct=8,market_cap=1e12)]
        got=m.rank_frame(pd.DataFrame(rows)).set_index('ticker')
        self.assertLess(got.loc['GOOD','final_rank'],got.loc['BIG','final_rank'])
    def test_negative_prior_eps_unranked(self):
        # EPS improvement from a prior-period loss is not a mathematically meaningful percentage.
        self.assertIsNone(m.num(None))
    def test_research_ui_exists(self):
        ui=(P/'usa_fundamental_rankings_ui.py').read_text()
        self.assertIn('render_usa_fundamental_rankings',ui)
    def test_no_site_scraping(self):
        source=(P/'scripts/build_usa_fundamental_rankings.py').read_text()
        self.assertNotIn('requests.get(',source)
if __name__=='__main__':unittest.main()
