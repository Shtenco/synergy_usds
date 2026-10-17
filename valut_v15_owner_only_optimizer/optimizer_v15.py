from __future__ import annotations
from dataclasses import dataclass
import csv, math, random, statistics
from typing import List, Dict, Tuple

@dataclass
class Bar:
    block:int
    price:float
    volume:float=0.0
    net_flow:float=0.0

@dataclass
class Params:
    signal:str
    lookback:int
    hold:int
    size:float
    threshold:float

def load_csv(path:str)->List[Bar]:
    out=[]
    with open(path,newline="") as f:
        for r in csv.DictReader(f):
            out.append(Bar(
                int(r["block"]),float(r["price"]),
                float(r.get("pool_volume_usdc",0)),
                float(r.get("pool_net_usdc",0)),
            ))
    return out

def cost_per_leg(notional:float,fee_bps:float,gas:float,impact_bps:float=0.0)->float:
    return notional*(fee_bps+impact_bps)/10_000+gas

def break_even_roundtrip_pct(fee_bps:float,gas:float=.002,notional:float=10.0)->float:
    return (2*cost_per_leg(notional,fee_bps,gas))/notional

def features(bars:List[Bar],i:int,lookback:int)->Dict[str,float]:
    j=max(0,i-lookback)
    p0=bars[j].price; p1=bars[i].price
    ret=(p1/p0-1.0) if p0 else 0.0
    flow=sum(x.net_flow for x in bars[j:i+1])
    vol=sum(x.volume for x in bars[j:i+1])
    return {"ret":ret,"flow":flow,"volume":vol}

def make_signal(kind:str,f:Dict[str,float],threshold:float)->int:
    if kind=="momentum":
        return 1 if f["ret"]>threshold else (-1 if f["ret"]<-threshold else 0)
    if kind=="mean_reversion":
        return -1 if f["ret"]>threshold else (1 if f["ret"]<-threshold else 0)
    if kind=="flow":
        scale=max(1.0,f["volume"])
        x=f["flow"]/scale
        return 1 if x>threshold else (-1 if x<-threshold else 0)
    if kind=="hybrid_mom_flow":
        a=1 if f["ret"]>threshold else (-1 if f["ret"]<-threshold else 0)
        scale=max(1.0,f["volume"])
        x=f["flow"]/scale
        b=1 if x>threshold else (-1 if x<-threshold else 0)
        return a if a==b else 0
    raise ValueError(kind)

def replay(bars:List[Bar],p:Params,fee_bps:float=5.0,gas:float=.002,start_usdc=50.0,start_weth_usd=50.0)->Dict[str,float]:
    if len(bars)<2: raise ValueError("bars")
    usdc=start_usdc
    weth=start_weth_usd/bars[0].price
    pos=0
    entry_i=-1
    trades=0
    fees=0.0
    navs=[]
    for i,b in enumerate(bars):
        f=features(bars,i,p.lookback)
        sig=make_signal(p.signal,f,p.threshold)

        # close timed position
        if pos!=0 and i-entry_i>=p.hold:
            if pos>0:
                qty=min(weth,p.size/b.price)
                gross=qty*b.price
                c=cost_per_leg(gross,fee_bps,gas)
                weth-=qty; usdc+=max(0.0,gross-c)
                fees+=c
            else:
                # research model has no borrow. A short signal means reduce existing WETH exposure.
                pass
            pos=0; trades+=1

        if pos==0 and sig!=0:
            if sig>0 and usdc>=p.size:
                c=cost_per_leg(p.size,fee_bps,gas)
                spend=max(0.0,p.size-c)
                usdc-=p.size
                weth+=spend/b.price
                fees+=c
                pos=1; entry_i=i; trades+=1
            elif sig<0:
                qty=min(weth,p.size/b.price)
                if qty>0:
                    gross=qty*b.price
                    c=cost_per_leg(gross,fee_bps,gas)
                    weth-=qty; usdc+=max(0.0,gross-c)
                    fees+=c
                    # position remains flat; signal just reduces long inventory.
                    trades+=1

        navs.append(usdc+weth*b.price)

    final=usdc+weth*bars[-1].price
    max_nav=-1e99; max_dd=0.0
    for n in navs:
        max_nav=max(max_nav,n)
        if max_nav>0:max_dd=max(max_dd,1-n/max_nav)
    return {"final_nav":final,"pnl":final-100.0,"trades":trades,"costs":fees,"max_dd":max_dd}

def hold_benchmark(bars:List[Bar])->float:
    return 50.0+(50.0/bars[0].price)*bars[-1].price

def grid()->List[Params]:
    out=[]
    for s in ("momentum","mean_reversion","flow","hybrid_mom_flow"):
        for lb in (1,2,3,5,8,13,21):
            for h in (1,2,3,5,8,13):
                for size in (2.5,5.0,7.5,10.0):
                    for th in (0.0,0.00025,0.0005,0.001,0.002):
                        out.append(Params(s,lb,h,size,th))
    return out

def optimize_train_oos(bars:List[Bar],fee_bps:float=5.0,gas:float=.002,train_frac=.70)->Dict[str,object]:
    cut=max(30,min(len(bars)-20,int(len(bars)*train_frac)))
    train=bars[:cut]
    oos=bars[cut-1:]
    ranked=[]
    for p in grid():
        r=replay(train,p,fee_bps,gas)
        # Penalize drawdown and excessive turnover.
        score=r["final_nav"]-25*r["max_dd"]-0.001*r["trades"]
        ranked.append((score,p,r))
    ranked.sort(key=lambda x:x[0],reverse=True)
    best=ranked[0][1]
    train_r=ranked[0][2]
    oos_r=replay(oos,best,fee_bps,gas)
    bench=hold_benchmark(oos)
    return {
        "best":best.__dict__,
        "train":train_r,
        "oos":oos_r,
        "oos_hold_benchmark":bench,
        "oos_alpha_vs_hold":oos_r["final_nav"]-bench,
        "accepted":oos_r["final_nav"]>bench,
    }

def walk_forward(bars:List[Bar],fee_bps:float=5.0,gas:float=.002,train=150,test=50)->Dict[str,float]:
    alphas=[]; finals=[]; accepted=0; windows=0
    i=0
    while i+train+test<=len(bars):
        window=bars[i:i+train+test]
        r=optimize_train_oos(window,fee_bps,gas,train/(train+test))
        alphas.append(r["oos_alpha_vs_hold"])
        finals.append(r["oos"]["final_nav"])
        accepted += int(r["accepted"])
        windows+=1
        i+=test
    return {
        "windows":windows,
        "accept_rate":accepted/windows if windows else 0.0,
        "median_alpha":statistics.median(alphas) if alphas else 0.0,
        "mean_alpha":statistics.mean(alphas) if alphas else 0.0,
        "p05_alpha":sorted(alphas)[max(0,int(.05*len(alphas))-1)] if alphas else 0.0,
    }

def flat_null(blocks=50,price=2500.0,trade=10.0,fee_bps=30.0,gas=.002)->Dict[str,float]:
    # exactly one external trade per block, alternating buy/sell: pure QE churn null.
    per_leg=cost_per_leg(trade,fee_bps,gas)
    loss=blocks*per_leg
    qe_reported=blocks*abs(16.4-1.0)*trade
    return {"final_nav":100-loss,"loss":loss,"qe_internal_reported_excluded":qe_reported}

if __name__=="__main__":
    for f in (30,5,1):
        print(f,"bp route break-even roundtrip %",100*break_even_roundtrip_pct(f))
    print("flat QE null",flat_null())
