from __future__ import annotations
from dataclasses import dataclass, asdict
import argparse, csv, math, random, statistics
from typing import List, Dict, Tuple

START_ASSETS=100.0
SENIOR_LIABILITIES=50.0
BLOCKS=50
FLOW_USD=10.0
HARD_HF=1.50
TARGET_HF=1.80

@dataclass(frozen=True)
class Route:
    name: str
    pool: str
    fee_bps: float
    liquidity_usd: float
    fail_prob: float

ROUTES: Tuple[Route,...]=(
    Route("Pancake V3 WETH/USDC 0.01%","0x72ab388e2e2f6facef59e3c3fa2c4e29011c2d38",1.0,4_827_421.65,0.08),
    Route("Aerodrome Slipstream WETH/USDC 0.05%","0xb2cc224c1c9fee385f8ad6a55b4d94e92359dc59",5.0,10_140_000.0,0.03),
    Route("Aerodrome Slipstream3 WETH/USDC 0.05%","0x3fe04a59ebd38cf06080a6f60a98d124eb59392a",5.0,6_490_000.0,0.03),
    Route("Uniswap V3 WETH/USDC 0.30%","0x6c561b446416e1a00e8e93e221854d6ea4171372",30.0,128_614_644.53,0.0),
    Route("Aerodrome Slipstream WETH/USDC 0.01%","0xdbc6998296caa1652a810dc8d3baf4a8294330f1",1.0,145_220.0,0.12),
    Route("Sushiswap V3 WETH/USDC 0.30%","0x41595326aabe6132fc6c7ae71af087a3a9dbc9f6",30.0,20_993.37,0.20),
    Route("Uniswap V3 WETH/USDC 0.03%","0x18b497f71122622557e4634c47a05647ff859f47",3.0,4_953.24,0.25),
    Route("Aerodrome WETH/USDC","0x3548029694fbb241d45fb24ba0cd9c9d4e745f16",30.0,21_745.97,0.20),
)

@dataclass
class Config:
    k: int
    bridge_fee_bps: float
    qe_capacity_usd_per_block: float
    hot_inventory_band_usd: float

@dataclass
class Trial:
    final_assets: float
    min_hf: float
    gross_volume: float
    external_settlement: float
    fee_revenue: float
    execution_cost: float
    rejected_volume: float
    rebalances: int
    success: bool

def _poisson_approx(rng: random.Random, lam: float) -> int:
    if lam <= 0: return 0
    if lam < 20:
        # Knuth for small lambda
        L=math.exp(-lam); p=1.0; k=0
        while p>L:
            k+=1; p*=rng.random()
        return k-1
    return max(0,int(rng.gauss(lam,math.sqrt(lam))+0.5))

def _route_cost_bps(route: Route, settlement: float, slippage_floor_bps: float=0.4) -> float:
    # Conservative CPMM-style depth proxy. For $10-$500 residuals vs multi-million pools
    # this term is tiny; explicit fee tier dominates.
    depth_impact=2.0*settlement/max(route.liquidity_usd,1.0)*10_000
    return route.fee_bps + slippage_floor_bps + depth_impact

def _pick_route(rng: random.Random, settlement: float) -> Route|None:
    available=[r for r in ROUTES if rng.random()>=r.fail_prob]
    if not available: return None
    return min(available,key=lambda r:_route_cost_bps(r,settlement))

def fee_fill_rate(fee_bps: float, elasticity: float=0.012) -> float:
    # Scenario parameter, not a market fact. At <=20bp no demand haircut.
    return min(1.0,math.exp(-elasticity*max(0.0,fee_bps-20.0)))

def run_trial(
    cfg: Config,
    seed: int,
    blocks: int=BLOCKS,
    base_flow_usd: float=FLOW_USD,
    fee_elasticity: float=0.012,
    direction_phi: float=0.75,
    direction_sigma: float=0.08,
    size_sigma: float=0.22,
    gas_per_batch: float=0.005,
    adverse_bps: float=0.8,
    shock_prob: float=0.01,
    shock_mean_usd: float=0.10,
) -> Trial:
    rng=random.Random(seed)
    A=START_ASSETS; L=SENIOR_LIABILITIES
    skew=0.0; z=0.0
    gross=external=fees=costs=rejected=0.0
    rebalances=0; min_hf=A/L
    fill=fee_fill_rate(cfg.bridge_fee_bps,fee_elasticity)

    for _ in range(blocks):
        z=direction_phi*z+rng.gauss(0.0,direction_sigma)
        p=max(0.05,min(0.95,0.5+z))
        n=_poisson_approx(rng,cfg.k*fill)
        if n<=0: continue

        signed=[]; absolute=[]
        for _ in range(n):
            # lognormal with mean approximately base_flow_usd
            s=base_flow_usd*rng.lognormvariate(-0.5*size_sigma*size_sigma,size_sigma)
            d=1.0 if rng.random()<p else -1.0
            absolute.append(s); signed.append(d*s)

        block_gross=sum(absolute)
        if block_gross>cfg.qe_capacity_usd_per_block:
            scale=cfg.qe_capacity_usd_per_block/block_gross
            rejected += block_gross-cfg.qe_capacity_usd_per_block
            block_gross=cfg.qe_capacity_usd_per_block
            block_net=sum(signed)*scale
        else:
            block_net=sum(signed)

        gross += block_gross
        income=block_gross*cfg.bridge_fee_bps/10_000
        fees += income; A += income
        skew += block_net

        if abs(skew)>cfg.hot_inventory_band_usd:
            settlement=max(0.0,abs(skew)-0.5*cfg.hot_inventory_band_usd)
            route=_pick_route(rng,settlement)
            if route is not None and settlement>0:
                route_cost=_route_cost_bps(route,settlement)+adverse_bps
                c=settlement*route_cost/10_000 + gas_per_batch
                A-=c; costs+=c; external+=settlement; rebalances+=1
                skew=math.copysign(0.5*cfg.hot_inventory_band_usd,skew)

        if rng.random()<shock_prob:
            loss=rng.expovariate(1.0/shock_mean_usd)
            A-=loss; costs+=loss

        min_hf=min(min_hf,A/L)
        if min_hf<HARD_HF:
            break

    success=(A>=200.0 and min_hf>=HARD_HF)
    return Trial(A,min_hf,gross,external,fees,costs,rejected,rebalances,success)

def summarize(cfg: Config,trials: int=500,seed0: int=0) -> Dict[str,float]:
    rs=[run_trial(cfg,seed0+i) for i in range(trials)]
    finals=sorted(r.final_assets for r in rs)
    def q(p:float)->float:
        i=min(len(finals)-1,max(0,int(round((len(finals)-1)*p))))
        return finals[i]
    return {
        "k":cfg.k,
        "bridge_fee_bps":cfg.bridge_fee_bps,
        "qe_capacity":cfg.qe_capacity_usd_per_block,
        "hot_band":cfg.hot_inventory_band_usd,
        "success_rate":sum(r.success for r in rs)/trials,
        "median_final_assets":statistics.median(finals),
        "p05_final_assets":q(.05),
        "p95_final_assets":q(.95),
        "mean_gross_volume":statistics.mean(r.gross_volume for r in rs),
        "mean_external_settlement":statistics.mean(r.external_settlement for r in rs),
        "mean_fee_revenue":statistics.mean(r.fee_revenue for r in rs),
        "mean_execution_cost":statistics.mean(r.execution_cost for r in rs),
        "mean_rejected_volume":statistics.mean(r.rejected_volume for r in rs),
        "mean_rebalances":statistics.mean(r.rebalances for r in rs),
    }

def grid_search(trials: int=200) -> List[Dict[str,float]]:
    rows=[]
    for k in range(50,151,10):
        for fee in (15,20,25,30,35,40,50,60,70,80,90,100):
            for qe in (500,1000,1500,2000):
                for band in (10,20,30):
                    rows.append(summarize(Config(k,fee,qe,band),trials))
    rows.sort(key=lambda r:(r["success_rate"]>=0.5,r["median_final_assets"]),reverse=True)
    return rows

def accepted(r: Dict[str,float]) -> bool:
    return r["success_rate"]>=0.5 and r["median_final_assets"]>=200 and r["p05_final_assets"]>=200

def write_csv(path: str,rows: List[Dict[str,float]]) -> None:
    with open(path,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trials",type=int,default=200)
    ap.add_argument("--out",default="v11_grid.csv")
    args=ap.parse_args()
    rows=grid_search(args.trials)
    write_csv(args.out,rows)
    good=[r for r in rows if accepted(r)]
    print("accepted",len(good),"of",len(rows))
    for r in good[:10]: print(r)

if __name__=="__main__":
    main()
