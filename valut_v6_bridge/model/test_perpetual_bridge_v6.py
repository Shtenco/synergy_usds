import math
import unittest
from perpetual_bridge_v6 import CPMM, Bridge, cycle_a, run_scenario

class BridgeV6MathTest(unittest.TestCase):
    def test_cycle_a_requires_internal_overpricing(self):
        p=2500.0
        ext=CPMM(118_000_000/2/p,118_000_000/2,5)
        bridge=Bridge(4_500_000,600,2_700_000,120)
        cheap=CPMM(100,100*0.8*p,30)
        r=cycle_a(1,ext,cheap,bridge,1,0.0,False,False)
        self.assertLess(r.bot_pnl,0)

    def test_cycle_a_profit_is_lp_loss_minus_external_cost(self):
        p=2500.0
        ext=CPMM(118_000_000/2/p,118_000_000/2,5)
        internal=CPMM(100,3_000_000,30)
        bridge=Bridge(4_500_000,600,2_700_000,120)
        r=cycle_a(1,ext,internal,bridge,1,0.05,False,False)
        self.assertGreater(r.bot_pnl,0)
        self.assertGreater(r.lp_trade_loss,r.bot_pnl)
        self.assertLess(abs(r.conservation_error),1e-6)
        self.assertTrue(math.isclose(r.bridge_equity_before,r.bridge_equity_after_trade,rel_tol=0,abs_tol=1e-6))

    def test_unbacked_compensation_reduces_bridge_equity(self):
        p=2500.0
        ext=CPMM(118_000_000/2/p,118_000_000/2,5)
        internal=CPMM(100,3_000_000,30)
        bridge=Bridge(4_500_000,600,2_700_000,120)
        r=cycle_a(1,ext,internal,bridge,1,0.05,True,False)
        self.assertTrue(math.isclose(
            r.bridge_equity_after_rebase,
            r.bridge_equity_after_trade-r.compensation_mint_usds,
            rel_tol=0,abs_tol=1e-6))

    def test_reset_to_same_extreme_price_needs_about_two_sales_of_mint(self):
        p=2500.0
        ext=CPMM(118_000_000/2/p,118_000_000/2,5)
        internal=CPMM(100,3_000_000,30)
        bridge=Bridge(4_500_000,600,2_700_000,120)
        r=cycle_a(1,ext,internal,bridge,1,0.05,False,True,target_internal_price=30_000)
        ratio=r.reset_mint_usds/r.usds_received
        self.assertGreater(ratio,1.9)
        self.assertLess(ratio,2.2)

    def test_repeated_zero_loss_reset_is_finite_under_hf_floor(self):
        s=run_scenario(cycles=100,bridge_assets_usd=6_000_000,bridge_liabilities_usd=3_000_000)
        self.assertLess(s['summary']['cycles_completed'],100)
        self.assertIsNotNone(s['summary']['stopped'])

if __name__=='__main__':
    unittest.main()
