from __future__ import annotations
from dataclasses import dataclass
import math, random, statistics
from typing import Dict, List

START_ASSETS=100.0
SENIOR_LIABILITIES=50.0
BLOCKS=50
MEAN_FLOW_USD=10.0
HARD_HF=1.50

@dataclass
class ControllerState:
    eta_est: float=0.020
    inventory_skew: float=0.0
    assets: float=100.0
    liabilities: float=50.0
    qe_capacity: float=2000.0
    hot_band: float=20.0

class AdaptiveFeeControllerV12:
    def __init__(self, ref_fee_bps=10.0, eta_init=0.020, ewma=0.20,
                 min_fee=10.0, max_fee=120.0,
                 heal_discount_bps=15.0, worsen_surcharge_bps=20.0):
        self.ref_fee_bps=ref_fee_bps
        self.eta_est=eta_init
        self.ewma=ewma
        self.min_fee=min_fee
        self.max_fee=max_fee
        self.heal_discount_bps=heal_discount_bps
        self.worsen_surcharge_bps=worsen_surcharge_bps

    def base_fee_bps(self) -> float:
        # Revenue-maximizing point for f*exp(-eta*(f-ref)).
        if self.eta_est<=0: return self.max_fee
        return max(self.min_fee,min(self.max_fee,self.ref_fee_bps+1.0/self.eta_est))

    def quote_fee_bps(self, direction:int, skew:float, band:float, demand_ratio:float=1.0) -> float:
        f=self.base_fee_bps()
        intensity=min(1.0,abs(skew)/max(band,1e-9))
        if skew!=0:
            if direction*skew>0: f += self.worsen_surcharge_bps*intensity
            else: f -= self.heal_discount_bps*intensity
        f += 5.0*(demand_ratio-1.0)
        return max(self.min_fee,min(self.max_fee,f))

    def observe_fill(self, quoted_fee_bps:float, fill_ratio:float) -> None:
        d=max(1e-9,quoted_fee_bps-self.ref_fee_bps)
        if d<=1e-8 or fill_ratio<=0 or fill_ratio>=1: return
        obs=-math.log(fill_ratio)/d
        obs=max(0.001,min(0.10,obs))
        self.eta_est=(1-self.ewma)*self.eta_est+self.ewma*obs

    def qe_capacity_for(self, requested_gross:float) -> float:
        # Virtual/junior capacity only. Never added to canonical NAV.
        return max(500.0,min(2500.0,1.20*requested_gross))

    def inventory_band_for_hf(self,hf:float) -> float:
        # High HF allows wider hot inventory and fewer external settlements.
        if hf>=2.2: return 30.0
        if hf>=2.0: return 25.0
        if hf>=1.8: return 20.0
        if hf>=1.7: return 15.0
        return 10.0

def acceptance_probability(fee_bps:float,eta:float,ref_fee_bps:float=10.0)->float:
    return min(1.0,math.exp(-eta*max(0.0,fee_bps-ref_fee_bps)))

def external_cost(settlement:float,fee_bps:float=5.0,gas:float=0.005,
                  adverse_bps:float=0.8,liquidity_usd:float=128_614_644.53)->float:
    # Deep external pool fallback. Depth impact is tiny at our scale but charged explicitly.
    impact_bps=2.0*settlement/max(liquidity_usd,1.0)*10_000
    return settlement*(fee_bps+adverse_bps+impact_bps)/10_000+gas

def _poisson(rng:random.Random,lam:float)->int:
    if lam<20:
        L=math.exp(-lam); p=1.0; k=0
        while p>L:
            k+=1; p*=rng.random()
        return k-1
    return max(0,int(rng.gauss(lam,math.sqrt(lam))+0.5))

def run_trial(seed:int=0,k:int=200,true_eta:float=0.020,
              adaptive:bool=True,fixed_fee_bps:float=35.0)->Dict[str,float]:
    rng=random.Random(seed)
    ctl=AdaptiveFeeControllerV12()
    A=START_ASSETS; L=SENIOR_LIABILITIES
    skew=0.0; z=0.0
    gross=fees=external=costs=rejected=0.0
    min_hf=A/L
    for _ in range(BLOCKS):
        demand_mult=max(.35,min(1.8,rng.lognormvariate(-.5*.18*.18,.18)))
        n=_poisson(rng,k*demand_mult)
        z=.75*z+rng.gauss(0,.08)
        pdir=max(.05,min(.95,.5+z))
        orders=[]
        potential=0.0
        for _ in range(n):
            s=MEAN_FLOW_USD*rng.lognormvariate(-.5*.22*.22,.22)
            d=1 if rng.random()<pdir else -1
            orders.append((d,s)); potential+=s

        hf=A/L if L else float("inf")
        band=ctl.inventory_band_for_hf(hf)
        qe_cap=ctl.qe_capacity_for(potential)
        accepted=[]
        quoted_weight=0.0; filled_weight=0.0
        demand_ratio=potential/max(k*MEAN_FLOW_USD,1e-9)
        for d,s in orders:
            f=ctl.quote_fee_bps(d,skew,band,demand_ratio) if adaptive else fixed_fee_bps
            quoted_weight+=s
            if rng.random()<=acceptance_probability(f,true_eta):
                accepted.append((d,s,f))
                filled_weight+=s

        if adaptive and quoted_weight>0:
            # Use gross quote/fill observation to update elasticity.
            avg_fee=(sum(s*f for _,s,f in accepted)/filled_weight) if filled_weight>0 else ctl.base_fee_bps()
            fill_ratio=max(1e-6,min(.999999,filled_weight/quoted_weight))
            ctl.observe_fill(avg_fee,fill_ratio)

        block_gross=sum(s for _,s,_ in accepted)
        if block_gross>qe_cap:
            scale=qe_cap/block_gross
            rejected+=block_gross-qe_cap
        else:
            scale=1.0
        block_signed=0.0; block_fees=0.0
        for d,s,f in accepted:
            ss=s*scale
            block_signed+=d*ss
            block_fees+=ss*f/10_000
        block_gross*=scale
        A+=block_fees; fees+=block_fees; gross+=block_gross
        skew+=block_signed

        if abs(skew)>band:
            settle=max(0.0,abs(skew)-.5*band)
            c=external_cost(settle)
            A-=c; costs+=c; external+=settle
            skew=math.copysign(.5*band,skew)

        min_hf=min(min_hf,A/L)
        if min_hf<HARD_HF: break

    return {
        "final_assets":A,
        "min_hf":min_hf,
        "gross_volume":gross,
        "external_settlement":external,
        "fee_revenue":fees,
        "execution_cost":costs,
        "rejected_volume":rejected,
        "eta_final":ctl.eta_est,
    }

def summarize(trials:int=300,**kwargs)->Dict[str,float]:
    rs=[run_trial(seed=i,**kwargs) for i in range(trials)]
    finals=sorted(r["final_assets"] for r in rs)
    q=lambda p: finals[int(round((len(finals)-1)*p))]
    return {
        "median_final_assets":statistics.median(finals),
        "p05_final_assets":q(.05),
        "p95_final_assets":q(.95),
        "success_rate":sum(r["final_assets"]>=200 and r["min_hf"]>=HARD_HF for r in rs)/trials,
        "mean_gross_volume":statistics.mean(r["gross_volume"] for r in rs),
        "mean_external_settlement":statistics.mean(r["external_settlement"] for r in rs),
        "mean_fee_revenue":statistics.mean(r["fee_revenue"] for r in rs),
        "mean_execution_cost":statistics.mean(r["execution_cost"] for r in rs),
        "mean_eta_final":statistics.mean(r["eta_final"] for r in rs),
    }

def optimize_k(max_k:int=500,trials:int=100,true_eta:float=.020)->List[Dict[str,float]]:
    rows=[]
    for k in range(50,max_k+1,25):
        r=summarize(trials=trials,k=k,true_eta=true_eta,adaptive=True)
        r["k"]=k
        rows.append(r)
    rows.sort(key=lambda x:x["median_final_assets"],reverse=True)
    return rows

if __name__=="__main__":
    print("fixed35",summarize(k=150,true_eta=.020,adaptive=False,fixed_fee_bps=35,trials=300))
    print("adaptive150",summarize(k=150,true_eta=.020,adaptive=True,trials=300))
    print("adaptive200",summarize(k=200,true_eta=.020,adaptive=True,trials=300))
    print("top K",optimize_k(500,50)[:10])
