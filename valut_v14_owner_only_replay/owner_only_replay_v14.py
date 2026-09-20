from __future__ import annotations
from dataclasses import dataclass, asdict
import argparse, csv, json, math, random
from typing import List

START_NAV=100.0
TRADE_USD=10.0
UNIV3_FEE_BPS=30.0

@dataclass
class Bar:
    block:int
    price:float
    swap_count:int=0
    pool_volume_usdc:float=0.0
    pool_net_usdc:float=0.0

@dataclass
class State:
    usdc:float
    weth:float
    internal_qe_usds:float=0.0
    internal_qe_eths:float=0.0
    internal_reported_pnl:float=0.0
    external_fees_paid:float=0.0
    gas_paid:float=0.0
    trades:int=0

    def nav(self,price:float)->float:
        # QE balances and internal reported PnL are intentionally excluded.
        return self.usdc+self.weth*price

def load_bars(path:str)->List[Bar]:
    out=[]
    with open(path,newline="") as f:
        for r in csv.DictReader(f):
            out.append(Bar(
                block=int(r["block"]),price=float(r["price"]),
                swap_count=int(float(r.get("swap_count",0))),
                pool_volume_usdc=float(r.get("pool_volume_usdc",0)),
                pool_net_usdc=float(r.get("pool_net_usdc",0)),
            ))
    if len(out)<2: raise ValueError("need >=2 bars")
    return out

def internal_qe_recharge(s:State,gradient_multiple:float,price:float)->None:
    # Own fork pool + own bridge + own arb contract: internal mint/reprice is not canonical profit.
    # We keep a research ledger only to prove that it can be arbitrarily large without changing NAV.
    s.internal_qe_usds += abs(gradient_multiple-1.0)*TRADE_USD
    s.internal_qe_eths += abs(gradient_multiple-1.0)*TRADE_USD/max(price,1e-9)
    s.internal_reported_pnl += abs(gradient_multiple-1.0)*TRADE_USD

def buy_weth_external(s:State,price:float,usd:float,gas_usd:float,impact_bps:float=0.0)->float:
    usd=min(usd,s.usdc)
    if usd<=0:return 0.0
    fee=usd*(UNIV3_FEE_BPS+impact_bps)/10_000
    spend=max(0.0,usd-fee)
    qty=spend/price
    s.usdc-=usd
    s.weth+=qty
    s.external_fees_paid+=fee
    s.usdc=max(0.0,s.usdc-gas_usd)
    s.gas_paid+=gas_usd
    s.trades+=1
    return qty

def sell_weth_external(s:State,price:float,usd_value:float,gas_usd:float,impact_bps:float=0.0)->float:
    qty=min(s.weth,usd_value/price)
    if qty<=0:return 0.0
    gross=qty*price
    fee=gross*(UNIV3_FEE_BPS+impact_bps)/10_000
    s.weth-=qty
    s.usdc+=gross-fee
    s.external_fees_paid+=fee
    s.usdc=max(0.0,s.usdc-gas_usd)
    s.gas_paid+=gas_usd
    s.trades+=1
    return qty

def signal(mode:str,i:int,bars:List[Bar],lookback:int,rng:random.Random)->int:
    if mode=="no_trade": return 0
    if mode=="alternating": return 1 if i%2==0 else -1
    if mode=="random": return 1 if rng.random()<.5 else -1
    j=max(0,i-lookback)
    ret=bars[i].price-bars[j].price
    if mode=="momentum": return 1 if ret>0 else (-1 if ret<0 else 0)
    if mode=="mean_reversion": return -1 if ret>0 else (1 if ret<0 else 0)
    raise ValueError(mode)

def replay(
    bars:List[Bar],mode:str="alternating",lookback:int=1,
    trade_usd:float=TRADE_USD,gas_usd:float=.002,
    qe_gradient_multiple:float=16.4,seed:int=1,
    start_usdc:float=50.0,start_weth_usd:float=50.0,
):
    p0=bars[0].price
    s=State(start_usdc,start_weth_usd/p0)
    rng=random.Random(seed)
    nav0=s.nav(p0)
    rows=[]
    for i,b in enumerate(bars):
        # QE can recharge the own fork gradient every block, but it has zero consolidated NAV effect.
        internal_qe_recharge(s,qe_gradient_multiple,b.price)
        sig=signal(mode,i,bars,lookback,rng)
        if sig>0:
            buy_weth_external(s,b.price,trade_usd,gas_usd)
        elif sig<0:
            sell_weth_external(s,b.price,trade_usd,gas_usd)
        rows.append({
            "block":b.block,"price":b.price,"signal":sig,
            "canonical_nav":s.nav(b.price),
            "usdc":s.usdc,"weth":s.weth,
            "qe_reported_pnl":s.internal_reported_pnl,
            "fees":s.external_fees_paid,"gas":s.gas_paid,
        })
    nav1=s.nav(bars[-1].price)
    return {
        "mode":mode,"lookback":lookback,"trade_usd":trade_usd,
        "start_nav":nav0,"final_nav":nav1,"pnl":nav1-nav0,
        "roi":nav1/nav0-1,"trades":s.trades,
        "external_fees_paid":s.external_fees_paid,"gas_paid":s.gas_paid,
        "qe_reported_pnl_excluded":s.internal_reported_pnl,
        "rows":rows,
    }

def optimize(bars:List[Bar],train_frac:float=.70):
    cut=max(2,min(len(bars)-2,int(len(bars)*train_frac)))
    train=bars[:cut]; test=bars[cut-1:]
    candidates=[]
    for mode in ("alternating","random","momentum","mean_reversion","no_trade"):
        for lb in (1,2,3,5,8,13,21):
            if mode in ("alternating","random","no_trade") and lb!=1: continue
            for trade in (2.5,5.0,7.5,10.0):
                r=replay(train,mode,lb,trade)
                candidates.append((r["final_nav"],mode,lb,trade))
    candidates.sort(reverse=True)
    _,mode,lb,trade=candidates[0]
    oos=replay(test,mode,lb,trade)
    hold=replay(test,"no_trade",1,0.0)
    return {
        "selected":{"mode":mode,"lookback":lb,"trade_usd":trade},
        "oos":{k:v for k,v in oos.items() if k!="rows"},
        "oos_no_trade":{k:v for k,v in hold.items() if k!="rows"},
        "train_bars":len(train),"oos_bars":len(test),
    }

def unchanged_price_round_trip(price:float=2500.0,trade_usd:float=10.0,gas_usd:float=.002):
    bars=[Bar(1,price),Bar(2,price)]
    # force buy then sell by alternating
    return replay(bars,"alternating",1,trade_usd,gas_usd)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--last",type=int,default=50)
    ap.add_argument("--json-out",default="v14_result.json")
    args=ap.parse_args()
    bars=load_bars(args.csv)
    if args.last>0: bars=bars[-args.last:]
    result={
        "owner_only_consolidated":True,
        "alternating_qe":{k:v for k,v in replay(bars,"alternating").items() if k!="rows"},
        "momentum":{k:v for k,v in replay(bars,"momentum",3).items() if k!="rows"},
        "mean_reversion":{k:v for k,v in replay(bars,"mean_reversion",3).items() if k!="rows"},
        "no_trade":{k:v for k,v in replay(bars,"no_trade",trade_usd=0).items() if k!="rows"},
        "optimized_train_oos":optimize(bars),
    }
    with open(args.json_out,"w") as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
