import unittest
from monte_carlo_v11 import Config, run_trial, summarize, accepted, ROUTES

class V11Test(unittest.TestCase):
    def test_eight_routes_registered(self):
        self.assertEqual(len(ROUTES),8)

    def test_qe_capacity_is_not_nav(self):
        a=run_trial(Config(110,20,500,20),seed=7)
        b=run_trial(Config(110,20,5000,20),seed=7)
        # QE only changes accepted throughput; it is never added directly to assets.
        self.assertLessEqual(a.gross_volume,b.gross_volume)
        self.assertNotEqual(a.final_assets,100+500)

    def test_no_fee_does_not_double_nav(self):
        r=summarize(Config(150,0,2000,20),trials=50)
        self.assertLess(r["median_final_assets"],200)

    def test_20bp_110flow_candidate_hits_target_in_scenario(self):
        r=summarize(Config(110,20,1500,20),trials=200)
        self.assertGreaterEqual(r["success_rate"],0.5)
        self.assertGreaterEqual(r["median_final_assets"],200)

    def test_acceptance_is_strict(self):
        r=summarize(Config(110,20,1500,20),trials=200)
        self.assertTrue(accepted(r))

if __name__=="__main__":
    unittest.main()
