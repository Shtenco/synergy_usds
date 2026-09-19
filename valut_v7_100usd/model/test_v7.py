import unittest
from optimize_v7 import run, optimize_bootstrap

class V7Test(unittest.TestCase):
    def test_nav_rebase_preserves_lp(self):
        r=run(full_price_reset=False,owner_share=.4,reserve_share=.6,insurance_share=0,burn_share=0)
        self.assertAlmostEqual(r.lp_fair_nav,50.0,places=9)

    def test_nav_rebase_beats_full_reset(self):
        old=run(full_price_reset=True)
        new=run(full_price_reset=False)
        self.assertGreater(new.cycles,old.cycles*4)
        self.assertGreater(new.owner_paid,old.owner_paid*4)

    def test_bootstrap_40_60_is_safer_for_same_owner_cashflow(self):
        split=run(full_price_reset=False)
        safe=run(full_price_reset=False,owner_share=.4,reserve_share=.6,insurance_share=0,burn_share=0)
        self.assertAlmostEqual(split.owner_paid,safe.owner_paid,places=9)
        self.assertGreater(safe.health_factor,split.health_factor)

    def test_optimizer_respects_hf(self):
        _,_,_,r=optimize_bootstrap()
        self.assertGreaterEqual(r.health_factor,1.5)
        self.assertGreater(r.owner_paid,20)

if __name__=="__main__":
    unittest.main()
