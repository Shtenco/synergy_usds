from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass
class State:
    canonical_usdc: float=50.0
    canonical_weth_value: float=50.0
    bridge_usd_inventory: float=25.0
    bridge_eth_inventory_value: float=25.0
    q_usds: float=0.0
    q_eths_value: float=0.0
    arb_cash: float=0.0
    internal_transfer_pnl: float=0.0
    external_costs: float=0.0

    @property
    def canonical_nav(self)->float:
        # Protocol-owned bridge inventory is already part of canonical holdings;
        # do not double-count it here.
        return self.canonical_usdc+self.canonical_weth_value-self.external_costs

def qe_recharge(s:State,target_multiple:float,notional:float)->None:
    # Virtual printing can recharge the shadow gradient without touching canonical NAV.
    excess=max(0.0,target_multiple-1.0)*notional
    s.q_usds += excess
    s.q_eths_value += excess

def cycle_a(s:State,notional:float=10.0,gradient_multiple:float=1.10,route_cost_bps:float=6.0):
    """
    Internal ETHS expensive:
    USDC -> external WETH -> bridge -> fork sell -> USDS -> USD bridge -> USDC.

    Executor PnL is the route spread. Because all bridge/fork pools are protocol-owned,
    the same internal transfer is recorded separately from canonical NAV.
    """
    gross_spread=notional*(gradient_multiple-1.0)
    external_cost=notional*route_cost_bps/10_000
    arb_pnl=gross_spread-external_cost

    # executor receives internal route profit
    s.arb_cash += arb_pnl
    s.internal_transfer_pnl += gross_spread
    s.external_costs += external_cost

    # bridge inventory skew: USD side pays out, ETH side receives canonical value.
    s.bridge_usd_inventory -= min(s.bridge_usd_inventory,gross_spread)
    s.bridge_eth_inventory_value += notional

    return arb_pnl

def cycle_b(s:State,notional:float=10.0,gradient_multiple:float=.90,route_cost_bps:float=6.0):
    """
    Internal ETHS cheap: reverse direction.
    """
    gross_spread=notional*(1.0-gradient_multiple)
    external_cost=notional*route_cost_bps/10_000
    arb_pnl=gross_spread-external_cost

    s.arb_cash += arb_pnl
    s.internal_transfer_pnl += gross_spread
    s.external_costs += external_cost

    # reverse inventory pressure
    s.bridge_usd_inventory += notional
    s.bridge_eth_inventory_value -= min(s.bridge_eth_inventory_value,gross_spread)

    return arb_pnl

def rebalance_direction(s:State)->str:
    # Very simple research controller: choose the direction that repairs the more depleted bridge.
    if s.bridge_usd_inventory < 20.0:
        return "B"
    if s.bridge_eth_inventory_value < 20.0:
        return "A"
    return "A"

def simulate(blocks:int=50,notional:float=10.0,up_gradient:float=1.10,down_gradient:float=.90):
    s=State()
    rows=[]
    for b in range(blocks):
        qe_recharge(s,max(up_gradient,1/down_gradient),notional)
        d=rebalance_direction(s)
        pnl=cycle_a(s,notional,up_gradient) if d=="A" else cycle_b(s,notional,down_gradient)
        rows.append({
            "block":b+1,
            "direction":d,
            "arb_executor_pnl":pnl,
            "arb_cash":s.arb_cash,
            "canonical_nav":s.canonical_nav,
            "bridge_usd_inventory":s.bridge_usd_inventory,
            "bridge_eth_inventory_value":s.bridge_eth_inventory_value,
            "q_usds":s.q_usds,
        })
    return s,rows

if __name__=="__main__":
    s,rows=simulate()
    print("arb executor pnl",s.arb_cash)
    print("consolidated canonical nav",s.canonical_nav)
    print("external costs",s.external_costs)
    print("bridge usd",s.bridge_usd_inventory,"bridge eth",s.bridge_eth_inventory_value)
