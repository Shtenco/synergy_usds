from __future__ import annotations
from dataclasses import dataclass, asdict
import argparse, csv, json, math, random, statistics
from typing import Dict, List, Tuple

BPS=10_000
START_ASSETS=100.0
START_LIABILITIES=50.0

@dataclass(frozen=True)
class Route:
    name: str
    fee_bps: float
    liquidity_usd: float
    availability: float

ROUTES: Tuple[Route,...]=(
    Route("Pancake V3 WETH/USDC 0.01%",1.0,4_800_000.0,0.90),
    Route("Aerodrome Slipstream WETH/USDC 0.05%",5.0,10_100_000.0,0.98),
    Route("Uniswap V3 WETH/USDC 0.30%",30.0,117_000_000.0,1.00),
)

@dataclass
class Policy:
    target_hf: float=1.80
    hard_hf: float=1.50
    max_trade_fraction: float=0.10
    min_safety_edge_bps: float=2.0
    gas_per_leg_usd: float=0.002
    qe_min: float=500.0
    qe_max: float=10_000.0
    escrow_target_fraction: float=0.20

@dataclass
class State:
    canonical_assets: float=START_ASSETS
    circulating_senior: float=START_LIABILITIES
    escrowed_senior: float=0.0
    virtual_qe: float=0.0
    realized_external_pnl: float=0.0
    external_costs: float=0.0
    trades: int=0
    skipped: int=0
    paused: bool=False

    @property
    def hf(self)->float:
        return math.inf if self.circulating_senior<=0 else self.canonical_assets/self.circulating_senior

    @property
    def canonical_surplus(self)->float:
        return self.canonical_assets-1.8*self.circulating_senior

@dataclass
class Signal:
    win_probability: float
    abs_move_fraction: float
    opportunity: bool=True

@dataclass
class Decision:
    execute: bool
    route: str
    notional: float
    expected_edge_fraction: float
    roundtrip_cost_fraction: float
    qe_target: float
    escrow_target: float
    reason: str

def roundtrip_cost_fraction(route:Route,notional:float,policy:Policy)->float:
    fee=2*route.fee_bps/BPS
    gas=2*policy.gas_per_leg_usd/max(notional,1e-12)
    impact=4*notional/max(route.liquidity_usd,1.0)
    return fee+gas+impact

def expected_edge_fraction(sig:Signal,cost_fraction:float)->float:
    return (2*sig.win_probability-1)*sig.abs_move_fraction-cost_fraction

def choose_route(notional:float,policy:Policy,availability_draw:float=0.0)->Tuple[Route,float]:
    viable=[]
    for r in ROUTES:
        if availability_draw<=r.availability:
            c=roundtrip_cost_fraction(r,notional,policy)
            viable.append((c,r))
    if not viable:
        r=ROUTES[-1]
        return r,roundtrip_cost_fraction(r,notional,policy)
    c,r=min(viable,key=lambda x:x[0])
    return r,c

def qe_target(sig:Signal,inventory_stress:float,policy:Policy)->float:
    confidence=max(0.0,min(1.0,2*abs(sig.win_probability-.5)))
    x=policy.qe_min+(policy.qe_max-policy.qe_min)*(0.65*confidence+0.35*min(1.0,inventory_stress))
    return max(policy.qe_min,min(policy.qe_max,x))

def escrow_target(state:State,policy:Policy)->float:
    # Pre-minted senior held inside owned contracts; not circulating liability.
    return min(
        policy.escrow_target_fraction*state.canonical_assets,
        max(0.0,state.canonical_assets/policy.target_hf-state.circulating_senior)
    )

def decide(state:State,sig:Signal,policy:Policy,rng:random.Random)->Decision:
    q=qe_target(sig,0.0,policy)
    esc=escrow_target(state,policy)
    if state.paused or state.hf<policy.hard_hf:
        return Decision(False,"",0,0,0,q,esc,"HF_PAUSE")
    if not sig.opportunity:
        return Decision(False,"",0,0,0,q,esc,"NO_OPPORTUNITY")

    notional=policy.max_trade_fraction*state.canonical_assets
    route,cost=choose_route(notional,policy,rng.random())
    edge=expected_edge_fraction(sig,cost)
    safety=policy.min_safety_edge_bps/BPS
    if edge<=safety:
        return Decision(False,route.name,notional,edge,cost,q,esc,"EDGE_TOO_SMALL")

    return Decision(True,route.name,notional,edge,cost,q,esc,"EXECUTE")

def apply_internal_policy(state:State,d:Decision)->None:
    # QE and escrow are internal capacity only.
    state.virtual_qe=d.qe_target
    state.escrowed_senior=d.escrow_target

def execute_stochastic(state:State,sig:Signal,d:Decision,policy:Policy,rng:random.Random)->float:
    apply_internal_policy(state,d)
    if not d.execute:
        state.skipped+=1
        return 0.0

    win=rng.random()<sig.win_probability
    gross_move=d.notional*sig.abs_move_fraction*(1 if win else -1)
    cost=d.notional*d.roundtrip_cost_fraction
    pnl=gross_move-cost

    state.canonical_assets+=pnl
    state.realized_external_pnl+=pnl
    state.external_costs+=cost
    state.trades+=1

    if state.hf<policy.hard_hf:
        state.paused=True
    return pnl

def execute_expected(state:State,sig:Signal,d:Decision,policy:Policy)->float:
    apply_internal_policy(state,d)
    if not d.execute:
        state.skipped+=1
        return 0.0
    pnl=d.notional*d.expected_edge_fraction
    state.canonical_assets+=pnl
    state.realized_external_pnl+=pnl
    state.external_costs+=d.notional*d.roundtrip_cost_fraction
    state.trades+=1
    if state.hf<policy.hard_hf:
        state.paused=True
    return pnl

def simulate_expected(
    blocks:int,
    hit_rate:float,
    move_fraction:float,
    opportunity_rate:float=1.0,
    seed:int=1,
    policy:Policy|None=None,
)->Dict[str,float]:
    policy=policy or Policy()
    state=State()
    rng=random.Random(seed)
    for _ in range(blocks):
        sig=Signal(hit_rate,move_fraction,rng.random()<opportunity_rate)
        d=decide(state,sig,policy,rng)
        execute_expected(state,sig,d,policy)
    return {
        "blocks":blocks,
        "final_nav":state.canonical_assets,
        "profit":state.canonical_assets-START_ASSETS,
        "roi":state.canonical_assets/START_ASSETS-1,
        "hf":state.hf,
        "trades":state.trades,
        "skipped":state.skipped,
        "qe_virtual_final":state.virtual_qe,
        "escrowed_senior_final":state.escrowed_senior,
        "circulating_senior":state.circulating_senior,
        "realized_external_pnl":state.realized_external_pnl,
        "external_costs":state.external_costs,
    }

def monte_carlo(
    blocks:int,
    hit_rate:float,
    move_fraction:float,
    opportunity_rate:float=1.0,
    trials:int=1000,
    policy:Policy|None=None,
)->Dict[str,float]:
    policy=policy or Policy()
    finals=[]
    pauses=0
    trades=[]
    for t in range(trials):
        state=State()
        rng=random.Random(10_000+t)
        for _ in range(blocks):
            sig=Signal(hit_rate,move_fraction,rng.random()<opportunity_rate)
            d=decide(state,sig,policy,rng)
            execute_stochastic(state,sig,d,policy,rng)
        finals.append(state.canonical_assets)
        pauses+=int(state.paused)
        trades.append(state.trades)
    finals.sort()
    q=lambda p: finals[int(round((len(finals)-1)*p))]
    return {
        "blocks":blocks,
        "trials":trials,
        "median_nav":statistics.median(finals),
        "p05_nav":q(.05),
        "p95_nav":q(.95),
        "prob_profit":sum(x>START_ASSETS for x in finals)/trials,
        "prob_double":sum(x>=2*START_ASSETS for x in finals)/trials,
        "pause_rate":pauses/trials,
        "mean_trades":statistics.mean(trades),
    }

def break_even_hit_rate(move_fraction:float,route_fee_bps:float=5.0,notional:float=10.0,gas_per_leg=.002)->float:
    route=Route("tmp",route_fee_bps,10_000_000,1)
    policy=Policy(gas_per_leg_usd=gas_per_leg)
    c=roundtrip_cost_fraction(route,notional,policy)
    return .5*(1+c/max(move_fraction,1e-12))

def required_external_edge_for_target(target_multiple:float,blocks:int,trade_fraction=.10,opportunity_rate=1.0)->float:
    n=max(1.0,blocks*opportunity_rate)
    return (target_multiple**(1/n)-1)/trade_fraction

def scenario_table()->List[Dict[str,float]]:
    rows=[]
    cases=[
        ("weak",.60,.005,.50),
        ("good",.65,.010,1.00),
        ("strong",.70,.010,1.00),
        ("rare_strong",.70,.010,.25),
        ("large_move",.65,.020,.50),
    ]
    for name,p,m,q in cases:
        for blocks in (50,500,5000):
            r=simulate_expected(blocks,p,m,q)
            r.update({"scenario":name,"hit_rate":p,"move":m,"opportunity_rate":q})
            rows.append(r)
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--json-out",default="v17_results.json")
    ap.add_argument("--mc-trials",type=int,default=1000)
    args=ap.parse_args()

    result={
        "break_even_hit_rate":{
            "move_0.25pct":break_even_hit_rate(.0025),
            "move_0.50pct":break_even_hit_rate(.005),
            "move_1.00pct":break_even_hit_rate(.01),
            "move_2.00pct":break_even_hit_rate(.02),
        },
        "required_edge_to_double":{
            "50_blocks":required_external_edge_for_target(2,50),
            "500_blocks":required_external_edge_for_target(2,500),
            "5000_blocks":required_external_edge_for_target(2,5000),
        },
        "scenarios":scenario_table(),
        "mc_good_5000":monte_carlo(5000,.65,.01,1,args.mc_trials),
        "mc_strong_500":monte_carlo(500,.70,.01,1,args.mc_trials),
    }
    with open(args.json_out,"w") as f:
        json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
