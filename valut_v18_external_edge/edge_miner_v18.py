from __future__ import annotations
from dataclasses import dataclass,asdict
import argparse,csv,json,math,statistics
from typing import Dict,List,Tuple

POOLS=("uniswap30","pancake1","aerodrome5","aerodrome3_5")
FEE_BPS={"uniswap30":30.0,"pancake1":1.0,"aerodrome5":5.0,"aerodrome3_5":5.0}
LIQ_USD={"uniswap30":128_600_000.0,"pancake1":4_800_000.0,"aerodrome5":10_100_000.0,"aerodrome3_5":8_190_000.0}
GAS_PER_LEG=0.002
NOTIONAL=10.0

@dataclass
class Row:
    block:int
    values:Dict[str,float]

@dataclass
class Rule:
    feature:str
    sign:int
    threshold:float
    horizon:int
    target_move:float

def fnum(x):
    try:return float(x)
    except:return float("nan")

def load(path)->List[Row]:
    out=[]
    with open(path,newline="") as f:
        for r in csv.DictReader(f):
            vals={k:fnum(v) for k,v in r.items() if k!="block"}
            out.append(Row(int(r["block"]),vals))
    return out

def median(xs):
    xs=[x for x in xs if math.isfinite(x)]
    return statistics.median(xs) if xs else float("nan")

def pct(a,b):
    return a/b-1 if b and math.isfinite(a) and math.isfinite(b) else 0.0

def features(rows:List[Row],i:int)->Dict[str,float]:
    v=rows[i].values
    prices=[v.get(f"{p}_price",float("nan")) for p in POOLS]
    prices=[x for x in prices if math.isfinite(x) and x>0]
    p=median(prices)
    if not math.isfinite(p): return {}
    out={}
    for lb in (1,2,3,5,8,13,21):
        j=max(0,i-lb)
        pj=median([rows[j].values.get(f"{q}_price",float("nan")) for q in POOLS])
        out[f"mom_{lb}"]=pct(p,pj)
        hist=[]
        for k in range(max(0,i-lb),i+1):
            pk=median([rows[k].values.get(f"{q}_price",float("nan")) for q in POOLS])
            if math.isfinite(pk): hist.append(pk)
        if len(hist)>2:
            rets=[hist[z]/hist[z-1]-1 for z in range(1,len(hist))]
            out[f"vol_{lb}"]=statistics.pstdev(rets)
        else: out[f"vol_{lb}"]=0.0

    if prices:
        out["spread"]=(max(prices)-min(prices))/p
    total_vol=sum(v.get(f"{q}_volume",0) for q in POOLS)
    total_flow=sum(v.get(f"{q}_netflow",0) for q in POOLS)
    out["flow_imbalance"]=total_flow/max(total_vol,1.0)
    out["volume"]=total_vol
    prev=sum(rows[max(0,i-1)].values.get(f"{q}_volume",0) for q in POOLS)
    out["volume_accel"]=math.log1p(total_vol)-math.log1p(prev)
    out["swap_count"]=sum(v.get(f"{q}_swaps",0) for q in POOLS)

    # Cross-venue relative premium to consensus.
    for q in POOLS:
        qp=v.get(f"{q}_price",float("nan"))
        out[f"premium_{q}"]=pct(qp,p) if math.isfinite(qp) else 0.0
    return out

def consensus_price(row:Row)->float:
    return median([row.values.get(f"{p}_price",float("nan")) for p in POOLS])

def future_return(rows:List[Row],i:int,h:int)->float:
    if i+h>=len(rows): return float("nan")
    a=consensus_price(rows[i]); b=consensus_price(rows[i+h])
    return pct(b,a)

def route_cost_fraction(pool:str,notional=NOTIONAL)->float:
    fee=2*FEE_BPS[pool]/10_000
    gas=2*GAS_PER_LEG/notional
    impact=4*notional/LIQ_USD[pool]
    return fee+gas+impact

def best_route()->Tuple[str,float]:
    return min(((p,route_cost_fraction(p)) for p in POOLS),key=lambda x:x[1])

def evaluate_rule(rows:List[Row],rule:Rule,start:int,end:int)->Dict[str,float]:
    route,cost=best_route()
    n=hits=move_hits=0; pnl=0.0; wins=0
    for i in range(max(21,start),min(end,len(rows)-rule.horizon)):
        fs=features(rows,i)
        x=fs.get(rule.feature)
        if x is None: continue
        fire=(rule.sign*x)>=rule.threshold
        if not fire: continue
        direction=1 if rule.sign>0 else -1
        r=future_return(rows,i,rule.horizon)
        if not math.isfinite(r): continue
        n+=1
        directional=direction*r
        if directional>0: hits+=1
        if directional>=rule.target_move: move_hits+=1
        trade_ret=directional-cost
        pnl += NOTIONAL*trade_ret
        if trade_ret>0:wins+=1
    return {
      "n":n,
      "hit_rate":hits/n if n else 0,
      "target_hit_rate":move_hits/n if n else 0,
      "profitable_rate":wins/n if n else 0,
      "pnl":pnl,
      "pnl_per_trade":pnl/n if n else 0,
      "route":route,
      "cost_fraction":cost,
    }

def candidate_rules(rows:List[Row],start:int,end:int)->List[Rule]:
    sample=[]
    for i in range(max(21,start),min(end,len(rows)-21)):
        sample.append(features(rows,i))
    names=sorted({k for d in sample for k in d})
    rules=[]
    for name in names:
        vals=sorted(abs(d.get(name,0)) for d in sample if math.isfinite(d.get(name,0)))
        if len(vals)<30: continue
        for q in (.50,.60,.70,.80,.90,.95):
            th=vals[min(len(vals)-1,int(q*(len(vals)-1)))]
            for sign in (-1,1):
                for h in (1,2,3,5,8,13,21):
                    for tm in (.0025,.005,.01,.02):
                        rules.append(Rule(name,sign,th,h,tm))
    return rules

def score(m:Dict[str,float])->float:
    if m["n"]<20:return -1e9
    # Profit first, then robustness/hit rate; no reward for internal QE.
    return m["pnl"] + 2*m["pnl_per_trade"] + .05*m["n"]

def train_oos(rows:List[Row],train_frac=.70)->Dict[str,object]:
    cut=max(100,min(len(rows)-50,int(len(rows)*train_frac)))
    train_start=0; train_end=cut
    ranked=[]
    for r in candidate_rules(rows,train_start,train_end):
        m=evaluate_rule(rows,r,train_start,train_end)
        ranked.append((score(m),r,m))
    ranked.sort(key=lambda x:x[0],reverse=True)
    top=ranked[:50]
    tested=[]
    for _,r,tr in top:
        o=evaluate_rule(rows,r,cut-1,len(rows))
        tested.append((o["pnl"],r,tr,o))
    tested.sort(key=lambda x:x[0],reverse=True)
    # Report best TRAIN rule on OOS, not best OOS-picked rule, to avoid leakage.
    _,best,tr=ranked[0]
    oos=evaluate_rule(rows,best,cut-1,len(rows))
    return {
      "best_rule":asdict(best),
      "train":tr,
      "oos":oos,
      "train_rows":cut,
      "oos_rows":len(rows)-cut+1,
      "best_route":{"name":best_route()[0],"roundtrip_cost_fraction":best_route()[1]},
      "exploratory_top50_oos_max": tested[0][0] if tested else 0.0,
    }

def walk_forward(rows:List[Row],train=1000,test=250)->Dict[str,float]:
    i=0; alphas=[]; accepted=0; windows=0; hitrates=[]
    while i+train+test<=len(rows):
        sub=rows[i:i+train+test]
        r=train_oos(sub,train/(train+test))
        o=r["oos"]
        alphas.append(o["pnl"])
        hitrates.append(o["hit_rate"])
        accepted += int(o["pnl"]>0 and o["n"]>=20)
        windows+=1; i+=test
    return {
      "windows":windows,
      "positive_window_rate":accepted/windows if windows else 0.0,
      "median_oos_pnl":statistics.median(alphas) if alphas else 0.0,
      "mean_oos_pnl":statistics.mean(alphas) if alphas else 0.0,
      "median_hit_rate":statistics.median(hitrates) if hitrates else 0.0,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--json-out",default="v18_results.json")
    args=ap.parse_args()
    rows=load(args.csv)
    result={
      "rows":len(rows),
      "route_costs":{p:route_cost_fraction(p) for p in POOLS},
      "train_oos":train_oos(rows),
      "walk_forward":walk_forward(rows) if len(rows)>=1250 else {"windows":0},
    }
    with open(args.json_out,"w") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
