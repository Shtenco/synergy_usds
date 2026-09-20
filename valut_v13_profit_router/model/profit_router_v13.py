from __future__ import annotations
from dataclasses import dataclass
import math, random, statistics
from typing import List, Dict, Tuple

START_ASSETS=100.0
SENIOR_LIABILITIES=50.0
MEAN_ORDER_USD=10.0
BLOCKS=50
HARD_HF=1.50

@dataclass(frozen=True)
class ExternalRoute:
    name: str
    pool: str
    fee_bps: float
    liquidity_usd: float
    fail_prob: float

ROUTES: Tuple[ExternalRoute,...]=(
    ExternalRoute("Pancake V3 WETH/USDC 0.01%","0x72ab388e2e2f6facef59e3c3fa2c4e29011c2d38",1.0,4_610_000.0,0.08),
    ExternalRoute("Aerodrome Slipstream WETH/USDC 0.05%","0xb2cc224c1c9fee385f8ad6a55b4d94e92359dc59",5.0,11_100_000.0,0.03),
    ExternalRoute("Aerodrome Slipstream3 WETH/USDC 0.05%","0x3fe04a59ebd38cf06080a6f60a98d124eb59392a",5.0,7_750_000.0,0.03),
    ExternalRoute("Uniswap V3 WETH/USDC 0.30%","0x6c561b446416e1a00e8e93e221854d6ea4171372",30.0,128_614_644.53,0.0),
)

@dataclass
class OrderDecision:
    accepted: bool
    fee_bps: float
    internal_amount: float
    external_amount: float
    external_route: str
    canonical_revenue: float
    canonical_cost: float
    inventory_after: float
    qe_used: float

class ProfitMaxRouterV13:
    def __init__(
        self,
        eta: float=0.020,
        ref_fee_bps: float=10.0,
        heal_discount_bps: float=10.0,
        base_fee_shift_bps: float=0.0,
        qe_capacity_usd_per_block: float=2500.0,
    ):
        self.eta=eta
        self.ref_fee_bps=ref_fee_bps
        self.heal_discount_bps=heal_discount_bps
        self.base_fee_shift_bps=base_fee_shift_bps
        self.qe_capacity_usd_per_block=qe_capacity_usd_per_block

    def base_fee_bps(self) -> float:
        if self.eta<=0: return 120.0
        return max(10.0,min(120.0,self.ref_fee_bps+1.0/self.eta+self.base_fee_shift_bps))

    def fee_bps(self,direction:int,inventory_skew:float,band:float) -> float:
        f=self.base_fee_bps()
        if inventory_skew and direction*inventory_skew<0:
            intensity=min(1.0,abs(inventory_skew)/max(band,1e-9))
            f-=self.heal_discount_bps*intensity
        return max(10.0,min(120.0,f))

    def fill_probability(self,fee_bps:float) -> float:
        return min(1.0,math.exp(-self.eta*max(0.0,fee_bps-self.ref_fee_bps)))

    @staticmethod
    def inventory_band(hf:float) -> float:
        if hf>=2.5: return 35.0
        if hf>=2.2: return 30.0
        if hf>=2.0: return 25.0
        if hf>=1.8: return 20.0
        return 12.0

def external_cost(route:ExternalRoute,settlement:float,gas:float=.002,adverse_bps:float=.8)->float:
    impact_bps=2.0*settlement/max(route.liquidity_usd,1.0)*10_000
    return settlement*(route.fee_bps+adverse_bps+impact_bps)/10_000+gas

def choose_external_route(rng:random.Random,settlement:float)->ExternalRoute:
    available=[r for r in ROUTES if rng.random()>=r.fail_prob]
    if not available:
        return ROUTES[-1]
    return min(available,key=lambda r:external_cost(r,settlement))

def route_order(
    rng:random.Random,
    router:ProfitMaxRouterV13,
    size:float,
    direction:int,
    inventory_skew:float,
    hf:float,
    qe_used:float,
)->OrderDecision:
    band=router.inventory_band(hf)
    fee=router.fee_bps(direction,inventory_skew,band)
    if rng.random()>router.fill_probability(fee):
        return OrderDecision(False,fee,0,0,"",0,0,inventory_skew,qe_used)
    if qe_used+size>router.qe_capacity_usd_per_block:
        return OrderDecision(False,fee,0,0,"",0,0,inventory_skew,qe_used)

    qe_used+=size
    fee_revenue=size*fee/10_000
    proposed=inventory_skew+direction*size

    # First priority: opposite order/netting or already-funded bridge inventory.
    if abs(proposed)<=band:
        return OrderDecision(True,fee,size,0,"internal-net/buffer",fee_revenue,0,proposed,qe_used)

    # Split: keep a profit-maximizing amount in hot inventory and settle only the residual.
    candidates=(0.0,.25*band,.50*band,.75*band)
    best=None
    for target_abs in candidates:
        external_amt=max(0.0,abs(proposed)-target_abs)
        route=choose_external_route(rng,external_amt)
        c=external_cost(route,external_amt)
        # Mark-to-risk penalty: holding more inventory has an expected future canonical cost.
        hold_risk=.00002*(target_abs**2/max(band,1.0))
        score=c+hold_risk
        if best is None or score<best[0]:
            best=(score,external_amt,target_abs,route,c)

    _,external_amt,target_abs,route,cost=best
    after=math.copysign(target_abs,proposed)
    return OrderDecision(
        True,fee,size-external_amt,external_amt,route.name,
        fee_revenue,cost,after,qe_used
    )

def _poisson(rng:random.Random,lam:float)->int:
    return max(0,int(rng.gauss(lam,math.sqrt(max(lam,1.0)))+.5))

def run_trial(seed:int=0,k:int=200,eta:float=.020,blocks:int=BLOCKS)->Dict[str,float]:
    rng=random.Random(seed)
    router=ProfitMaxRouterV13(eta=eta)
    A=START_ASSETS; L=SENIOR_LIABILITIES
    skew=0.0; z=0.0
    gross=fee_revenue=external=costs=internal=0.0
    accepted=external_orders=0
    min_hf=A/L

    for _ in range(blocks):
        z=.75*z+rng.gauss(0,.08)
        pdir=max(.05,min(.95,.5+z))
        demand_mult=max(.4,min(1.6,rng.lognormvariate(-.5*.16*.16,.16)))
        n=_poisson(rng,k*demand_mult)
        qe_used=0.0

        for _ in range(n):
            size=MEAN_ORDER_USD*rng.lognormvariate(-.5*.22*.22,.22)
            direction=1 if rng.random()<pdir else -1
            d=route_order(rng,router,size,direction,skew,A/L,qe_used)
            qe_used=d.qe_used
            if not d.accepted: continue

            accepted+=1
            gross+=size
            internal+=d.internal_amount
            external+=d.external_amount
            if d.external_amount>0: external_orders+=1
            fee_revenue+=d.canonical_revenue
            costs+=d.canonical_cost
            A+=d.canonical_revenue-d.canonical_cost
            skew=d.inventory_after

        if rng.random()<.01:
            shock=rng.expovariate(10.0)
            A-=shock; costs+=shock

        min_hf=min(min_hf,A/L)
        if min_hf<HARD_HF:
            break

    return {
        "final_assets":A,
        "roi":A/START_ASSETS-1,
        "min_hf":min_hf,
        "gross_volume":gross,
        "internal_volume":internal,
        "external_settlement":external,
        "fee_revenue":fee_revenue,
        "canonical_cost":costs,
        "accepted_orders":accepted,
        "external_orders":external_orders,
    }

def summarize(k:int,trials:int=300,eta:float=.020)->Dict[str,float]:
    rs=[run_trial(i,k,eta) for i in range(trials)]
    finals=sorted(r["final_assets"] for r in rs)
    q=lambda p:finals[round((len(finals)-1)*p)]
    return {
        "k":k,
        "median_final_assets":statistics.median(finals),
        "p05_final_assets":q(.05),
        "p95_final_assets":q(.95),
        "success_rate":sum(r["final_assets"]>=200 and r["min_hf"]>=HARD_HF for r in rs)/trials,
        "mean_gross_volume":statistics.mean(r["gross_volume"] for r in rs),
        "mean_internal_volume":statistics.mean(r["internal_volume"] for r in rs),
        "mean_external_settlement":statistics.mean(r["external_settlement"] for r in rs),
        "mean_fee_revenue":statistics.mean(r["fee_revenue"] for r in rs),
        "mean_canonical_cost":statistics.mean(r["canonical_cost"] for r in rs),
        "mean_external_orders":statistics.mean(r["external_orders"] for r in rs),
    }

if __name__=="__main__":
    for k in (150,200,250):
        print(summarize(k))
