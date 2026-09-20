from __future__ import annotations
from dataclasses import dataclass
import itertools, math

START_NAV=100.0
PRICE=2500.0
TVL=118_000_000.0

@dataclass
class ExternalPool:
    weth: float
    usdc: float
    fee_bps: float

    @classmethod
    def from_tvl(cls,tvl=TVL,price=PRICE,fee_bps=1.0):
        usdc=tvl/2
        weth=(tvl/2)/price
        return cls(weth,usdc,fee_bps)

    def buy_weth(self,usdc_in:float)->float:
        f=1-self.fee_bps/10_000
        k=self.weth*self.usdc
        eff=usdc_in*f
        new_weth=k/(self.usdc+eff)
        out=self.weth-new_weth
        self.usdc += usdc_in
        self.weth -= out
        return out

    def sell_weth(self,weth_in:float)->float:
        f=1-self.fee_bps/10_000
        k=self.weth*self.usdc
        eff=weth_in*f
        new_usdc=k/(self.weth+eff)
        out=self.usdc-new_usdc
        self.weth += weth_in
        self.usdc -= out
        return out

@dataclass
class Protocol:
    canonical_usdc: float=50.0
    canonical_weth: float=50.0/PRICE
    bridge_usd: float=25.0
    bridge_weth: float=25.0/PRICE
    q_usds: float=0.0
    q_eths: float=0.0
    arb_executor_pnl: float=0.0
    gas_paid: float=0.0

    def nav(self,price=PRICE)->float:
        # bridge inventories are subsets of protocol canonical balances in the
        # consolidated view and are therefore not double-counted.
        return self.canonical_usdc+self.canonical_weth*price

def qe_recharge(p:Protocol,gradient:float,notional:float)->None:
    virtual=max(0.0,gradient-1.0)*notional
    p.q_usds += virtual
    p.q_eths += virtual/PRICE

def cycle_a(p:Protocol,e:ExternalPool,notional:float,gradient:float,gas_leg=.002):
    # consolidated external action: buy WETH. All later fork/bridge legs are internal.
    q=min(notional,p.canonical_usdc)
    weth=e.buy_weth(q)
    p.canonical_usdc -= q
    p.canonical_weth += weth
    p.gas_paid += gas_leg
    p.canonical_usdc -= min(p.canonical_usdc,gas_leg)

    # Internal executor can report this transfer profit; another owned pool loses it.
    p.arb_executor_pnl += q*max(0.0,gradient-1.0)
    return weth

def cycle_b_close(p:Protocol,e:ExternalPool,weth_amount:float,gradient:float,gas_leg=.002):
    q=min(weth_amount,p.canonical_weth)
    out=e.sell_weth(q)
    p.canonical_weth -= q
    p.canonical_usdc += out
    p.gas_paid += gas_leg
    p.canonical_usdc -= min(p.canonical_usdc,gas_leg)
    # Reverse internal transfer profit is still internal.
    p.arb_executor_pnl += out*max(0.0,gradient-1.0)
    return out

def closed_ab_loop(notional=10.0,gradient=16.4,fee_bps=1.0,gas_leg=.002):
    p=Protocol()
    e=ExternalPool.from_tvl(fee_bps=fee_bps)
    start=p.nav()
    qe_recharge(p,gradient,notional)
    weth=cycle_a(p,e,notional,gradient,gas_leg)
    qe_recharge(p,gradient,notional)
    cycle_b_close(p,e,weth,gradient,gas_leg)
    return {
        "gradient":gradient,
        "notional":notional,
        "fee_bps":fee_bps,
        "start_nav":start,
        "final_nav":p.nav(),
        "canonical_pnl":p.nav()-start,
        "arb_executor_pnl":p.arb_executor_pnl,
        "gas_paid":p.gas_paid,
        "q_usds":p.q_usds,
    }

def repeat_closed_loops(cycles=50,notional=10.0,gradient=16.4,fee_bps=1.0,gas_leg=.002):
    p=Protocol()
    e=ExternalPool.from_tvl(fee_bps=fee_bps)
    start=p.nav()
    for _ in range(cycles):
        qe_recharge(p,gradient,notional)
        weth=cycle_a(p,e,notional,gradient,gas_leg)
        qe_recharge(p,gradient,notional)
        cycle_b_close(p,e,weth,gradient,gas_leg)
    return {
        "cycles":cycles,
        "gradient":gradient,
        "fee_bps":fee_bps,
        "notional":notional,
        "start_nav":start,
        "final_nav":p.nav(),
        "canonical_pnl":p.nav()-start,
        "arb_executor_pnl":p.arb_executor_pnl,
        "gas_paid":p.gas_paid,
    }

def exogenous_move_loop(notional=10.0,external_move=0.001,fee_bps=1.0,gas_leg=.002):
    # Small-trade approximation: buy before an exogenous market move and sell after it.
    # This is deliberately classified as EXTERNAL alpha, not QE alpha.
    fee_cost=2*notional*fee_bps/10_000
    gas=2*gas_leg
    pnl=notional*external_move-fee_cost-gas
    return pnl

def exhaustive_search():
    best=None
    rows=[]
    for fee in (1.0,5.0,30.0):
        for g in (1.01,1.05,1.10,1.25,1.5,2.0,5.0,16.4,50.0,100.0):
            for n in (.10,.25,.50,1.0,2.5,5.0,7.5,10.0):
                r=closed_ab_loop(n,g,fee)
                rows.append(r)
                if best is None or r["canonical_pnl"]>best["canonical_pnl"]:
                    best=r
    return best,rows

if __name__=="__main__":
    for fee in (1,5,30):
        print("50 loops",repeat_closed_loops(fee_bps=fee))
    best,_=exhaustive_search()
    print("best closed loop",best)
    for move in (.0005,.0006,.001,.005,.01):
        print("external move",move,"pnl",exogenous_move_loop(external_move=move))
