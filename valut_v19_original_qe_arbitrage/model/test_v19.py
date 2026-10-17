import unittest
from original_loop_v19 import *

class V19OriginalLoopTest(unittest.TestCase):
    def test_qe_recharge_does_not_change_canonical_nav(self):
        s=State()
        n=s.canonical_nav
        qe_recharge(s,16.4,10)
        self.assertEqual(s.canonical_nav,n)
        self.assertGreater(s.q_usds,0)

    def test_cycle_a_can_show_executor_profit(self):
        s=State()
        p=cycle_a(s,10,1.10,6)
        self.assertGreater(p,0)
        self.assertGreater(s.arb_cash,0)

    def test_internal_executor_profit_is_not_double_counted_as_canonical_nav(self):
        s=State()
        n=s.canonical_nav
        cycle_a(s,10,1.10,6)
        self.assertLess(s.canonical_nav,n)

    def test_reverse_cycle_repairs_usd_bridge_inventory(self):
        s=State(bridge_usd_inventory=10)
        before=s.bridge_usd_inventory
        cycle_b(s,10,.90,6)
        self.assertGreater(s.bridge_usd_inventory,before)

if __name__=="__main__":
    unittest.main()
