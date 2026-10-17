# V18 — External Edge Miner

V18 does not modify QE economics. Its only job is to find a real, out-of-sample external signal that can feed V17 Dynamic Central Bank.

## Current Base venues

Research snapshot around 19-20 September 2026:

| venue | pool | fee | approximate liquidity / activity |
|---|---|---:|---|
| PancakeSwap V3 WETH/USDC | 0x72ab388e2e2f6facef59e3c3fa2c4e29011c2d38 | 0.01% | ~$4.8m liquidity, ~$57m 24h volume |
| Aerodrome SlipStream WETH/USDC | 0xb2cc224c1c9fee385f8ad6a55b4d94e92359dc59 | 0.05% | ~$10.1m liquidity, ~$21.9m 24h volume |
| Aerodrome Slipstream 3 WETH/USDC | 0x3fe04a59ebd38cf06080a6f60a98d124eb59392a | 0.05% | ~$8m-class liquidity, ~$47m 24h volume |
| Uniswap V3 WETH/USDC | 0x6c561b446416e1a00e8e93e221854d6ea4171372 | 0.30% | ~$128.6m liquidity, ~$81.6m 24h volume |

For our $10 trade the deepest pool is not necessarily the most profitable route. Fee dominates price impact.

## Round-trip cost at $10

Assuming $0.002 gas per leg and negligible impact:

```
Pancake 1bp each leg:
  2bp DEX + 4bp gas ~= 6bp

Aerodrome 5bp each leg:
  10bp DEX + 4bp gas ~= 14bp

Uniswap 30bp each leg:
  60bp DEX + 4bp gas ~= 64bp
```

This changes the predictive hurdle dramatically.

For symmetric directional prediction:

```
p_break_even = 0.5 * (1 + cost / expected_move)
```

Examples for Pancake 1bp route:

```
0.25% subsequent move -> p > 62%
0.50% subsequent move -> p > 56%
1.00% subsequent move -> p > 53%
2.00% subsequent move -> p > 51.5%
```

Therefore V18's first target is not necessarily p>57% at 1%; it is to maximize actual OOS dollar PnL after selecting the cheapest executable route.

## Real block data

`fetch_multivenue_base.py` fetches Base Swap logs for four venues and produces one aligned row per block with:

- close price by venue;
- USDC volume;
- signed USDC net flow;
- swap count.

## Features

Purely lagged/current features:

- momentum 1/2/3/5/8/13/21 blocks;
- realized volatility shock;
- cross-DEX spread;
- each venue premium/discount to median price;
- aggregate signed swap-flow imbalance;
- volume acceleration;
- swap-count intensity.

No future data enters features.

## Labels

Future consensus-price return at:

```
1,2,3,5,8,13,21 blocks
```

and move targets:

```
0.25%, 0.50%, 1%, 2%
```

## Search

The miner generates threshold rules from TRAIN quantiles only. Rules are ranked on TRAIN by external dollar PnL after route cost. The single best TRAIN rule is frozen and evaluated on OOS.

An exploratory top-50 OOS statistic is also reported but is explicitly not accepted evidence because selecting it would leak OOS information.

## Walk-forward

For sufficiently long data:

```
1000 block train
250 block OOS
roll forward by 250
```

A candidate edge is useful to V17 only when multiple OOS windows remain profitable.

## Acceptance gate for V17

The external trade gate should only be enabled if:

1. OOS PnL > 0 after cheapest-route cost;
2. sample count is large enough;
3. multiple walk-forward windows are positive;
4. result survives a higher gas/fee stress;
5. feature uses only information available before execution.

QE amount is absent from the objective. V18 cannot manufacture profit through internal accounting.

## Run

```bash
cd valut_v18_external_edge
python3 fetch_multivenue_base.py \
  --rpc https://mainnet.base.org \
  --blocks 5000 \
  --out v18_multivenue.csv

python3 edge_miner_v18.py v18_multivenue.csv \
  --json-out v18_results.json
```
