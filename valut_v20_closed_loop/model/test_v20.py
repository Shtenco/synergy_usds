import unittest
from closed_loop_v20 import *

class V20ClosedLoopTest(unittest.TestCase):
    def test_qe_size_cannot_change_canonical_nav(self):
        a=closed_ab_loop(10,1.01,1)
        b=closed_ab_loop(10,100,1)
        self.assertAlmostEqual(a["canonical_pnl"],b["canonical_pnl"],places=9)
        self.assertGreater(b["arb_executor_pnl"],a["arb_executor_pnl"])

    def test_closed_loop_loses_at_1bp(self):
        r=closed_ab_loop(10,16.4,1)
        self.assertLess(r["canonical_pnl"],0)
        self.assertAlmostEqual(r["canonical_pnl"],-.006,delta=.0001)

    def test_50_loops_about_9970(self):
        r=repeat_closed_loops(50,10,16.4,1)
        self.assertAlmostEqual(r["final_nav"],99.70,delta=.001)

    def test_higher_external_fee_is_worse(self):
        a=closed_ab_loop(10,16.4,1)
        b=closed_ab_loop(10,16.4,30)
        self.assertLess(b["canonical_pnl"],a["canonical_pnl"])

    def test_exhaustive_grid_finds_no_positive_closed_loop(self):
        best,rows=exhaustive_search()
        self.assertLess(best["canonical_pnl"],0)

    def test_positive_external_move_can_create_real_profit(self):
        self.assertGreater(exogenous_move_loop(10,.001,1,.002),0)

if __name__=="__main__":
    unittest.main()
