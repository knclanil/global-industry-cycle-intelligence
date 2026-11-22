import unittest
import pandas as pd
from usa_graph_membership_ranks import enrich_membership_summary

class TestRankJoin(unittest.TestCase):
    def test_sort_keep_unranked_and_ties(self):
        membership=pd.DataFrame({'Company':['Alpha','Bravo','Charlie','Delta'],'Ticker':['A','B','C','D'],'Factor':['Value']*4})
        ranks=pd.DataFrame({'ticker':['A','B','C','D'], 'ranking_eligible':[True,True,False,True],
                            'final_rank':[2,1,None,1], 'total_fundamental_rank':[9,7,None,7],
                            'roe':[20,25,None,25], 'roe_rank':[2,1,None,1],
                            'market_cap':[10,20,None,20]})
        out,details,counts=enrich_membership_summary(membership,ranks)
        self.assertEqual(out['Ticker'].tolist(),['B','D','A','C'])
        self.assertEqual(counts['ranked'],3)
        self.assertEqual(len(out),4)
        self.assertEqual(details.loc[0,'ROE %'],25)
        self.assertTrue(pd.isna(out.loc[3,'Final Rank']))
    def test_missing_data_keeps_every_company(self):
        rows=pd.DataFrame({'Company':['Alpha'],'Ticker':['A']})
        ranks=pd.DataFrame({'ticker':['B'],'ranking_eligible':[True], 'final_rank':[1], 'total_fundamental_rank':[5]})
        out, _, _=enrich_membership_summary(rows,ranks)
        self.assertEqual(len(out),1)
        self.assertTrue(pd.isna(out.iloc[0]['Final Rank']))
    def test_ambiguous_ticker_refuses_to_guess(self):
        rows=pd.DataFrame({'Company':['Alpha'],'Ticker':['A']})
        ranks=pd.DataFrame({'ticker':['A','A'],'ranking_eligible':[True,True], 'final_rank':[1,2], 'total_fundamental_rank':[5,6]})
        out, _, _=enrich_membership_summary(rows,ranks)
        self.assertTrue(pd.isna(out.iloc[0]['Final Rank']))

if __name__=='__main__':unittest.main()
