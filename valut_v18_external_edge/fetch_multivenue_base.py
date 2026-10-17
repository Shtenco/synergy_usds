#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,time,urllib.request
from collections import defaultdict

SWAP_TOPIC="0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
Q96=2**96
POOLS={
 "uniswap30":"0x6c561b446416e1a00e8e93e221854d6ea4171372",
 "pancake1":"0x72ab388e2e2f6facef59e3c3fa2c4e29011c2d38",
 "aerodrome5":"0xb2cc224c1c9fee385f8ad6a55b4d94e92359dc59",
 "aerodrome3_5":"0x3fe04a59ebd38cf06080a6f60a98d124eb59392a",
}

def rpc(url,method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(url,data=body,headers={"content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as r: out=json.load(r)
    if "error" in out: raise RuntimeError(out["error"])
    return out["result"]

def sint(word):
    x=int(word,16)
    return x-(1<<256) if x>=(1<<255) else x

def decode(log):
    data=log["data"][2:]
    w=[data[i:i+64] for i in range(0,len(data),64)]
    if len(w)<3: return None
    a0=sint(w[0]); a1=sint(w[1]); sqrtp=int(w[2],16)
    price=(sqrtp/Q96)**2*1e12
    if not (100<price<100_000): return None
    return {
      "block":int(log["blockNumber"],16),
      "amount0_weth":a0/1e18,
      "amount1_usdc":a1/1e6,
      "price":price,
    }

def fetch_logs(url,pool,start,end,chunk):
    out=[]; a=start
    while a<=end:
        b=min(end,a+chunk-1)
        try:
            part=rpc(url,"eth_getLogs",[{
              "fromBlock":hex(a),"toBlock":hex(b),"address":pool,"topics":[SWAP_TOPIC]
            }])
            out.extend(part); a=b+1
        except Exception:
            if chunk<=1: raise
            chunk=max(1,chunk//2)
            continue
        time.sleep(.02)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rpc",required=True)
    ap.add_argument("--blocks",type=int,default=5000)
    ap.add_argument("--end-block",type=int)
    ap.add_argument("--chunk",type=int,default=50)
    ap.add_argument("--out",default="v18_multivenue.csv")
    args=ap.parse_args()
    end=args.end_block or int(rpc(args.rpc,"eth_blockNumber",[]),16)
    start=max(0,end-args.blocks+1)

    agg={name:defaultdict(list) for name in POOLS}
    counts={}
    for name,pool in POOLS.items():
        raw=fetch_logs(args.rpc,pool,start,end,args.chunk)
        dec=[decode(x) for x in raw]
        dec=[x for x in dec if x]
        counts[name]=len(dec)
        for x in dec: agg[name][x["block"]].append(x)

    rows=[]; last={}
    for b in range(start,end+1):
        row={"block":b}
        any_price=False
        for name in POOLS:
            xs=agg[name].get(b,[])
            if xs:
                last[name]=xs[-1]["price"]; any_price=True
                row[f"{name}_price"]=last[name]
                row[f"{name}_volume"]=sum(abs(x["amount1_usdc"]) for x in xs)
                row[f"{name}_netflow"]=sum(x["amount1_usdc"] for x in xs)
                row[f"{name}_swaps"]=len(xs)
            else:
                row[f"{name}_price"]=last.get(name,"")
                row[f"{name}_volume"]=0.0
                row[f"{name}_netflow"]=0.0
                row[f"{name}_swaps"]=0
        if any_price or any(v!="" for k,v in row.items() if k.endswith("_price")):
            rows.append(row)

    fields=["block"]
    for name in POOLS:
        fields += [f"{name}_price",f"{name}_volume",f"{name}_netflow",f"{name}_swaps"]
    with open(args.out,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(json.dumps({"start":start,"end":end,"rows":len(rows),"logs":counts,"out":args.out},indent=2))

if __name__=="__main__": main()
