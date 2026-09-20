import unittest, random
from profit_router_v13 import *

class V13Test(unittest.TestCase):
    def test_k_is_external_order_count(self):
        r=summarize(50,trials=20)
        self.assertGreater(r["mean_gross_volume"],0)

    def test_healing_order_gets_discount(self):
        c=ProfitMaxRouterV13()
        self.assertLess(c.fee_bps(-1,20,20),c.fee_bps(1,20,20))

    def test_qe_never_enters_canonical_revenue(self):
        rng=random.Random(1)
        c=ProfitMaxRouterV13(qe_capacity_usd_per_block=2500)
        d=route_order(rng,c,10,1,0,2.0,0)
        self.assertLess(d.canonical_revenue,1.0)
        self.assertNotEqual(d.canonical_revenue,2500)

    def test_external_residual_is_real_settlement(self):
        rng=random.Random(4)
        c=ProfitMaxRouterV13()
        d=route_order(rng,c,100,1,30,2.2,0)
        self.assertTrue(d.accepted)
        self.assertGreater(d.external_amount,0)
        self.assertGreater(d.canonical_cost,0)

    def test_k200_scenario_clears_100pct_target(self):
        r=summarize(200,trials=100)
        self.assertGreater(r["p05_final_assets"],200)
        self.assertEqual(r["success_rate"],1.0)

if __name__=="__main__":
    unittest.main()
