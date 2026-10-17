import unittest
from dynamic_cb_v17 import *

class V17Test(unittest.TestCase):
    def test_qe_does_not_change_nav(self):
        s=State()
        p=Policy()
        d=Decision(False,"",0,0,0,10000,10,"NO")
        apply_internal_policy(s,d)
        self.assertEqual(s.canonical_assets,100)
        self.assertEqual(s.circulating_senior,50)
        self.assertEqual(s.virtual_qe,10000)

    def test_external_trade_is_capped_at_10pct_nav(self):
        s=State()
        p=Policy()
        d=decide(s,Signal(.9,.05,True),p,__import__("random").Random(1))
        self.assertLessEqual(d.notional,.10*s.canonical_assets+1e-12)

    def test_no_positive_edge_means_no_trade(self):
        s=State()
        p=Policy()
        d=decide(s,Signal(.55,.001,True),p,__import__("random").Random(1))
        self.assertFalse(d.execute)

    def test_break_even_frontier_5bp(self):
        self.assertAlmostEqual(break_even_hit_rate(.0025),.78,places=2)
        self.assertAlmostEqual(break_even_hit_rate(.005),.64,places=2)
        self.assertAlmostEqual(break_even_hit_rate(.01),.57,places=2)

    def test_good_edge_grows_over_5000_blocks(self):
        r=simulate_expected(5000,.65,.01,1)
        self.assertGreater(r["final_nav"],200)
        self.assertGreater(r["hf"],1.8)

    def test_weak_edge_is_skipped_or_nonprofitable(self):
        r=simulate_expected(50,.60,.005,.5)
        self.assertLessEqual(r["final_nav"],100.1)

if __name__=="__main__":
    unittest.main()
