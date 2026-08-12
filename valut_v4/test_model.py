import importlib.util
import math
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("base_v5_mint_sell_pp.py")
SPEC = importlib.util.spec_from_file_location("base_model", MODULE_PATH)
MODEL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODEL)


class MintSellPPModelTest(unittest.TestCase):
    def test_all_stress_scenarios_restore_the_peg(self):
        for q in (0.001, 0.005, 0.01, 0.02, 0.05):
            for multiple in (1.0, 2.0, 3.0, 5.0):
                rows, summary = MODEL.run(q=q, cycles=100, m=multiple)
                self.assertEqual(len(rows), 100)
                self.assertTrue(math.isclose(summary["final_price"], 1.0))
                self.assertTrue(all(math.isclose(row.p_final, 1.0) for row in rows))

    def test_productive_principal_requires_about_twice_sale_proceeds(self):
        rows, _ = MODEL.run(q=0.001, cycles=1, m=3.0)
        first = rows[0]
        ratio = first.topup_to_peg / first.sale_proceeds
        self.assertGreater(ratio, 2.0)
        self.assertLess(ratio, 2.01)

    def test_three_x_value_added_surplus_includes_gas(self):
        for q in (0.001, 0.005, 0.01, 0.02, 0.05):
            rows, _ = MODEL.run(q=q, cycles=100, m=3.0)
            self.assertTrue(all(math.isclose(
                row.surplus, row.value_added - row.topup_to_peg - row.gas
            ) for row in rows))

    def test_return_denominator_includes_pool_and_pp_buffer(self):
        _, summary = MODEL.run(q=0.01, cycles=100, m=3.0)
        self.assertEqual(summary["initial_external_capital"], 2.0)
        expected = summary["cumulative_surplus_usdc"] / 2.0
        self.assertTrue(math.isclose(
            summary["distributable_surplus_per_initial_external_dollar"], expected
        ))


if __name__ == "__main__":
    unittest.main()
