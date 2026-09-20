import unittest
from printmoney_v16 import *

class V16Test(unittest.TestCase):
    def test_qe_can_be_huge_without_fake_nav(self):
        e=PrintMoneyEngineV16(qe_ceiling=1_000_000)
        nav=e.consolidated_nav()
        e.qe_expansion(500_000)
        self.assertEqual(e.consolidated_nav(),nav)
        self.assertEqual(e.s.external_senior_liabilities,50)

    def test_escrow_buffer_is_not_external_debt(self):
        e=PrintMoneyEngineV16(escrow_ceiling=100_000)
        e.fill_escrow_buffer(50_000)
        self.assertEqual(e.s.external_senior_liabilities,50)
        self.assertEqual(e.consolidated_nav(),100)

    def test_release_turns_internal_buffer_into_real_liability(self):
        e=PrintMoneyEngineV16()
        e.fill_escrow_buffer(12.5)
        e.release_escrow_against_canonical(12.5)
        self.assertAlmostEqual(e.s.canonical_assets,112.5)
        self.assertAlmostEqual(e.s.external_senior_liabilities,62.5)
        self.assertAlmostEqual(e.hf,1.8)

    def test_cannot_release_more_than_hf_supports(self):
        e=PrintMoneyEngineV16()
        e.fill_escrow_buffer(20)
        with self.assertRaises(ValueError):
            e.release_escrow_against_canonical(20)

    def test_sunrise_recharges_gradient_without_profit(self):
        e=PrintMoneyEngineV16()
        nav=e.consolidated_nav()
        e.sunrise(200,500)
        self.assertEqual(e.consolidated_nav(),nav)
        self.assertEqual(e.s.external_senior_liabilities,50)
        self.assertGreater(e.s.q_usds,0)
        self.assertEqual(e.s.escrowed_senior,500)

    def test_profit_or_revert(self):
        e=PrintMoneyEngineV16(min_profit_usd=.01)
        with self.assertRaises(ValueError):
            e.execute_external_profit(.02,.015)
        net=e.execute_external_profit(.05,.02)
        self.assertAlmostEqual(net,.03)
        self.assertAlmostEqual(e.consolidated_nav(),100.03)

    def test_only_real_profit_creates_fresh_seniorization_capacity(self):
        e=PrintMoneyEngineV16()
        e.fill_escrow_buffer(100)
        e.qe_expansion(10000)
        self.assertEqual(e.safe_seniorize_from_new_profit(100),0)
        e.execute_external_profit(.20,.02)
        self.assertAlmostEqual(e.safe_seniorize_from_new_profit(100),.18/1.8)

if __name__=="__main__":
    unittest.main()
