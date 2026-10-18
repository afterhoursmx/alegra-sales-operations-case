import unittest
from revenue_model import MARKETS, market_scenarios

class TestMarketRevenue(unittest.TestCase):
    def test_local_currency_and_distinct_segment_arpa(self):
        rows=[{'country':'Colombia','segment':'PyME','new_leads':100,'mql_share':.7,'historical_candidates':10,'arpa_local':60000},
              {'country':'Colombia','segment':'Contador','new_leads':100,'mql_share':.7,'historical_candidates':10,'arpa_local':100000},
              {'country':'Perú','segment':'Contador','new_leads':100,'mql_share':.7,'historical_candidates':10,'arpa_local':140}]
        res=market_scenarios(rows)
        self.assertEqual([r['currency'] for r in res],['COP','COP','PEN'])
        self.assertGreater(res[1]['incremental_mrr_local'],res[0]['incremental_mrr_local'])
        self.assertEqual(res[1]['inbound_incremental_wins'],res[0]['inbound_incremental_wins'])
    def test_negative_or_duplicate_rejected(self):
        row={'country':'México','segment':'PyME','new_leads':100,'mql_share':.7,'historical_candidates':10,'arpa_local':400}
        with self.assertRaises(ValueError): market_scenarios([row,row])
        with self.assertRaises(ValueError): market_scenarios([{**row,'arpa_local':-1}])
    def test_all_currencies(self):
        self.assertEqual(set(MARKETS.values()),{'MXN','COP','PEN','DOP'})

if __name__=='__main__': unittest.main()
