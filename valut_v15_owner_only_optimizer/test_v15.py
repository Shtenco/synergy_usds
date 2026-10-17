import unittest
from optimizer_v15 import *

class V15Test(unittest.TestCase):
    def test_flat_qe_null_loses(self):
        r=flat_null()
        self.assertAlmostEqual(r["final_nav"],98.4,places=9)
        self.assertAlmostEqual(r["qe_internal_reported_excluded"],7700,places=9)

    def test_break_even_costs(self):
        self.assertAlmostEqual(100*break_even_roundtrip_pct(30),.64,places=9)
        self.assertAlmostEqual(100*break_even_roundtrip_pct(5),.14,places=9)
        self.assertAlmostEqual(100*break_even_roundtrip_pct(1),.06,places=9)

    def test_qe_does_not_enter_optimizer_nav(self):
        bars=[Bar(i,2500) for i in range(250)]
        r=optimize_train_oos(bars,fee_bps=5)
        self.assertLessEqual(r["oos"]["final_nav"],100.000001)

    def test_price_signal_can_only_win_via_external_move(self):
        bars=[Bar(i,2500*(1.001**i)) for i in range(250)]
        r=optimize_train_oos(bars,fee_bps=5)
        self.assertGreater(r["oos_hold_benchmark"],100)

if __name__=="__main__":
    unittest.main()
