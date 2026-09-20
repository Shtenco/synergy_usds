#!/usr/bin/env python3
"""
Fetch real Uniswap V3 WETH/USDC Swap logs from Base and write one row per block.

No third-party Python packages required.
"""
from __future__ import annotations
import argparse, csv, json, time, urllib.request
from collections import defaultdict

POOL="0x6c561b446416e1a00e8e93e221854d6ea4171372"
SWAP_TOPIC="0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
Q96=2**96

def rpc(url,method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(url,data=body,headers={"content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as r:
        out=json.load(r)
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]

def sint(word):
    x=int(word,16)
    return x-(1<<256) if x >= (1<<255) else x

def decode(log):
    data=log["data"][2:]
    words=[data[i:i+64] for i in range(0,len(data),64)]
    if len(words)<5:
        raise ValueError("short Swap log")
    amount0=sint(words[0])
    amount1=sint(words[1])
    sqrt_price_x96=int(words[2],16)
    # token0=WETH(18d), token1=USDC(6d)
    price=(sqrt_price_x96/Q96)**2 * 1e12
    return {
        "block":int(log["blockNumber"],16),
        "tx":log["transactionHash"],
        "amount0_weth":amount0/1e18,
        "amount1_usdc":amount1/1e6,
        "price_usdc_per_weth":price,
    }

def fetch(url,start,end,chunk=20):
    logs=[]
    a=start
    while a<=end:
        b=min(end,a+chunk-1)
        part=rpc(url,"eth_getLogs",[{
            "fromBlock":hex(a),"toBlock":hex(b),
            "address":POOL,
            "topics":[SWAP_TOPIC],
        }])
        logs.extend(part)
        a=b+1
        time.sleep(0.03)
    return logs

def aggregate(decoded,start,end):
    by=defaultdict(list)
    for x in decoded:
        by[x["block"]].append(x)
    rows=[]
    last_price=None
    for block in range(start,end+1):
        xs=by.get(block,[])
        if xs:
            close=xs[-1]["price_usdc_per_weth"]
            last_price=close
            volume_usdc=sum(abs(x["amount1_usdc"]) for x in xs)
            volume_weth=sum(abs(x["amount0_weth"]) for x in xs)
            net_usdc=sum(x["amount1_usdc"] for x in xs)
            rows.append({
                "block":block,"price":close,"swap_count":len(xs),
                "pool_volume_usdc":volume_usdc,
                "pool_volume_weth":volume_weth,
                "pool_net_usdc":net_usdc,
            })
        elif last_price is not None:
            rows.append({
                "block":block,"price":last_price,"swap_count":0,
                "pool_volume_usdc":0.0,"pool_volume_weth":0.0,"pool_net_usdc":0.0,
            })
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rpc",required=True)
    ap.add_argument("--blocks",type=int,default=500)
    ap.add_argument("--end-block",type=int)
    ap.add_argument("--chunk",type=int,default=20)
    ap.add_argument("--out",default="base_weth_usdc_blocks.csv")
    args=ap.parse_args()
    end=args.end_block
    if end is None:
        end=int(rpc(args.rpc,"eth_blockNumber",[]),16)
    start=max(0,end-args.blocks+1)
    raw=fetch(args.rpc,start,end,args.chunk)
    decoded=[decode(x) for x in raw]
    rows=aggregate(decoded,start,end)
    if not rows:
        raise RuntimeError("no swap-derived prices in requested range")
    with open(args.out,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(json.dumps({
        "pool":POOL,"start":start,"end":end,
        "logs":len(decoded),"rows":len(rows),
        "first_price":rows[0]["price"],"last_price":rows[-1]["price"],
        "out":args.out
    },indent=2))

if __name__=="__main__":
    main()
