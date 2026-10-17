import unittest
from perpetual_ring_v8 import PerpetualBridgeRing, break_even_volume, perpetual_condition, demo_100usd

class V8PerpetualRingTest(unittest.TestCase):
    def test_no_edge_no_trade_no_decay(self):
        r=PerpetualBridgeRing()
        a0,l0=r.A,r.L
        for _ in range(1000):
            e=r.step(1.0,fee_margin_bps=1,variable_cost_bps=1,fixed_cost=.002)
            self.assertFalse(e.executed)
        self.assertEqual(r.A,a0); self.assertEqual(r.L,l0)

    def test_external_positive_edge_can_run_10000_epochs(self):
        d=demo_100usd(10_000)
        self.assertFalse(d['paused'])
        self.assertGreater(d['assets'],100)
        self.assertEqual(d['liabilities'],50)
        self.assertGreater(d['hf'],2.0)
        self.assertGreater(d['owner_paid'],0)

    def test_break_even_volume(self):
        self.assertAlmostEqual(break_even_volume(.002,10),2.0)
        self.assertAlmostEqual(break_even_volume(.002,5),4.0)

    def test_growth_condition_40_60_at_hf_180(self):
        self.assertAlmostEqual(perpetual_condition(.40,1.80,1.3333333333333333,1.0),0.0,places=12)

    def test_one_to_one_growth_headroom(self):
        r=PerpetualBridgeRing()
        self.assertAlmostEqual(r.max_one_to_one_liability_growth(),12.5)
        with self.assertRaises(ValueError): r.add_matched_deposit(12.51,12.51)
        r.add_matched_deposit(12.5,12.5)
        self.assertAlmostEqual(r.hf,1.8)

if __name__=='__main__': unittest.main()