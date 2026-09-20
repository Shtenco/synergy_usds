import unittest
from adaptive_controller_v12 import *

class V12Test(unittest.TestCase):
    def test_healing_flow_is_cheaper(self):
        c=AdaptiveFeeControllerV12()
        heal=c.quote_fee_bps(-1,20,20)
        harm=c.quote_fee_bps(1,20,20)
        self.assertLess(heal,harm)

    def test_qe_is_capacity_not_nav(self):
        r=run_trial(seed=1,k=50,true_eta=.02,adaptive=True)
        self.assertNotEqual(r["final_assets"],100+2500)
        self.assertGreaterEqual(r["final_assets"],75)

    def test_zero_external_demand_cannot_create_profit(self):
        r=run_trial(seed=2,k=0,true_eta=.02,adaptive=True)
        self.assertLessEqual(r["final_assets"],100.000001)

    def test_reference_adaptive_hits_100pct_target_at_k200(self):
        r=summarize(trials=100,k=200,true_eta=.02,adaptive=True)
        self.assertGreater(r["p05_final_assets"],200)
        self.assertEqual(r["success_rate"],1.0)

    def test_deep_pool_impact_on_10usd_is_tiny(self):
        fee=external_cost(10,fee_bps=0,gas=0,adverse_bps=0)
        self.assertLess(fee,0.000001)

if __name__=="__main__":
    unittest.main()
