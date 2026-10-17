import unittest
from owner_only_replay_v14 import Bar, State, internal_qe_recharge, replay, unchanged_price_round_trip

class V14OwnerOnlyTest(unittest.TestCase):
    def test_qe_does_not_change_consolidated_nav(self):
        s=State(50,0.02)
        n0=s.nav(2500)
        internal_qe_recharge(s,16.4,2500)
        self.assertAlmostEqual(s.nav(2500),n0,places=12)
        self.assertGreater(s.internal_reported_pnl,0)

    def test_internal_reported_profit_is_excluded(self):
        bars=[Bar(i,2500) for i in range(1,11)]
        r=replay(bars,"no_trade",trade_usd=0)
        self.assertAlmostEqual(r["final_nav"],100,places=9)
        self.assertGreater(r["qe_reported_pnl_excluded"],1000)

    def test_flat_market_qe_churn_loses_money(self):
        r=unchanged_price_round_trip(2500,10,.002)
        self.assertLess(r["final_nav"],r["start_nav"])
        self.assertGreater(r["external_fees_paid"],0)

    def test_no_trade_flat_market_preserves_nav(self):
        bars=[Bar(i,2500) for i in range(1,51)]
        r=replay(bars,"no_trade",trade_usd=0)
        self.assertAlmostEqual(r["final_nav"],100,places=9)

    def test_internal_ownership_consolidates_transfers(self):
        bars=[Bar(1,2500),Bar(2,2550),Bar(3,2525)]
        a=replay(bars,"no_trade",trade_usd=0,qe_gradient_multiple=1)
        b=replay(bars,"no_trade",trade_usd=0,qe_gradient_multiple=100)
        self.assertAlmostEqual(a["final_nav"],b["final_nav"],places=9)

if __name__=="__main__":
    unittest.main()
