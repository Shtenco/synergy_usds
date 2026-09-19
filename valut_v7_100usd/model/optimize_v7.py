from dataclasses import dataclass
import math

P=2500.0
EXT_TVL=118_000_000.0
EXT_FEE=0.0005
INT_FEE=0.003

@dataclass
class Result:
    cycles:int
    stop:str
    owner_paid:float
    gross_bot_pnl:float
    external_costs:float
    bridge_assets:float
    bridge_liabilities:float
    health_factor:float
    internal_price:float
    lp_fair_nav:float
    insurance:float

def external_buy(q):
    y=EXT_TVL/2
    x=y/P
    k=x*y
    return (k/(x-q)-y)/(1-EXT_FEE)

def internal_sell(x,y,q):
    eff=q*(1-INT_FEE)
    out=y-x*y/(x+eff)
    return x+q,y-out,out

def initial_pool(fork_nav,m):
    x=fork_nav/(P*(1+m))
    y=m*P*x
    return x,y

def run(m=12.0, trade_fraction=0.0125, gas=0.002,
        full_price_reset=False,
        owner_share=.40, reserve_share=.30, insurance_share=.20, burn_share=.10,
        total_real_capital=100.0, fork_nav=50.0, liabilities=50.0,
        min_hf=1.50, min_premium=1.01, max_cycles=10000):
    assert abs(owner_share+reserve_share+insurance_share+burn_share-1)<1e-12
    x,y=initial_pool(fork_nav,m)
    target=m*P
    lp_target=x*P+y
    A=total_real_capital
    L=liabilities
    owner=insurance=gross=costs=0.0
    stop="max"
    cycles=0
    for i in range(1,max_cycles+1):
        if y/x/P<=min_premium:
            stop="spread_exhausted"; break
        q=x*trade_fraction
        ext=external_buy(q)
        x2,y2,S=internal_sell(x,y,q)
        pnl=S-ext-gas
        if pnl<=0:
            stop="net_pnl_nonpositive"; break

        # Honest 1:1 bridge leg: canonical assets and redeemable liabilities
        # move by the same fair-value amount.
        A += q*P-S
        L += q*P-S

        if full_price_reset:
            mint=max(0.0,target*x2-y2)
        else:
            # V7: restore LP fair NAV only. Do NOT restore the artificial quote.
            mint=max(0.0,lp_target-(x2*P+y2))
        y2 += mint
        L += mint

        owner += owner_share*pnl
        A += reserve_share*pnl
        insurance += insurance_share*pnl
        # Optional debt retirement assumes accessible circulating USDS at par.
        L=max(0.0,L-burn_share*pnl)

        if L>0 and A/L<min_hf and insurance>0:
            need=min(insurance,max(0.0,min_hf*L-A))
            A+=need
            insurance-=need

        gross += pnl
        costs += (ext-q*P)+gas
        x,y=x2,y2
        cycles=i
        if L>0 and A/L<min_hf-1e-12:
            stop="hf_floor"; break

    return Result(
        cycles,stop,owner,gross,costs,A,L,
        math.inf if L<=0 else A/L,
        y/x,x*P+y,insurance
    )

def optimize_bootstrap(gas=0.002):
    best=None
    for mi in range(11,201):
        m=mi/10
        for ti in range(5,51):
            tf=ti/1000
            r=run(m=m,trade_fraction=tf,gas=gas,
                  owner_share=.40,reserve_share=.60,insurance_share=0,burn_share=0)
            if r.stop not in ("spread_exhausted","net_pnl_nonpositive"):
                continue
            if r.health_factor<1.50:
                continue
            if best is None or r.owner_paid>best[0]:
                best=(r.owner_paid,m,tf,r)
    return best

if __name__=="__main__":
    old=run(full_price_reset=True)
    nav=run(full_price_reset=False)
    boot=run(full_price_reset=False,owner_share=.40,reserve_share=.60,insurance_share=0,burn_share=0)
    opt=optimize_bootstrap()
    print("old_full_reset",old)
    print("nav_40_30_20_10",nav)
    print("bootstrap_40_60",boot)
    print("grid_best",opt)
