import unittest, tempfile, csv, math
from edge_miner_v18 import *

class V18Test(unittest.TestCase):
    def test_pancake_is_cheapest_route(self):
        name,cost=best_route()
        self.assertEqual(name,"pancake1")
        self.assertLess(cost,0.001)

    def test_cost_frontier(self):
        # 1bp each leg + $0.002 gas each leg on $10 ~= 6bp total.
        c=route_cost_fraction("pancake1")
        self.assertAlmostEqual(c,0.0006,delta=0.00002)

    def test_uniswap30_is_deep_but_expensive(self):
        self.assertGreater(route_cost_fraction("uniswap30"),route_cost_fraction("pancake1"))

    def test_feature_spread_and_flow(self):
        rows=[]
        for i in range(30):
            vals={}
            for p in POOLS:
                vals[f"{p}_price"]=2500+i+(1 if p=="pancake1" else 0)
                vals[f"{p}_volume"]=100
                vals[f"{p}_netflow"]=10
                vals[f"{p}_swaps"]=1
            rows.append(Row(i,vals))
        f=features(rows,29)
        self.assertGreater(f["spread"],0)
        self.assertGreater(f["flow_imbalance"],0)
        self.assertIn("mom_5",f)

    def test_no_rule_can_claim_internal_qe_profit(self):
        # V18 has no QE or internal-PnL field in its objective at all.
        rows=[]
        for i in range(100):
            vals={}
            for p in POOLS:
                vals[f"{p}_price"]=2500
                vals[f"{p}_volume"]=100
                vals[f"{p}_netflow"]=0
                vals[f"{p}_swaps"]=1
            rows.append(Row(i,vals))
        r=Rule("mom_1",1,0,1,.005)
        m=evaluate_rule(rows,r,0,len(rows))
        self.assertLessEqual(m["pnl"],0)

if __name__=="__main__": unittest.main()
