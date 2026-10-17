import unittest
from qe_bridge_v9 import *

class V9Test(unittest.TestCase):
    def test_trade_is_tiny_vs_external_pool(self):
        p=ExternalPool()
        self.assertLess(10/p.tvl,1e-6)

    def test_qe_reset_does_not_create_senior_liability(self):
        p=QEForkPool()
        s0=p.senior_usds
        q=ExternalPool().buy_weth_with_usdc(10)
        r=p.sell_eths_and_qe_reset(q)
        self.assertGreater(r['qe_mint'],0)
        self.assertLess(p.senior_usds,s0)
        self.assertGreater(p.qe_usds,0)

    def test_first_16x_cycle_is_not_perpetually_redeemable(self):
        r=run_qe_demo(1)[0]
        self.assertGreater(r['senior_redeemable_out'],30)
        self.assertGreater(r['qe_mint'],150)

    def test_bridge_netting_can_make_10usd_flow_positive(self):
        r=bridge_ring_revenue()
        self.assertAlmostEqual(r['external_settlement'],1.0)
        self.assertGreater(r['net_canonical_revenue'],0)

    def test_only_retained_canonical_revenue_supports_new_senior(self):
        self.assertAlmostEqual(safe_senior_recharge(.0096,1.8),.005333333333333333,places=12)

if __name__=='__main__': unittest.main()