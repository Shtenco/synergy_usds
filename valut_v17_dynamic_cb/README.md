# V17 — Dynamic Central Bank: clean canonical profit only

V17 continues V16 but changes the optimization target to one thing only:

```
MAX Delta Consolidated Canonical NAV
```

The system owns the fork pool, bridge pool, QE controller and arbitrage executor. Therefore internal fees, QE mint, escrow mint and internal swaps remain consolidated transfers and never count as profit.

## State controlled each Base block

The controller chooses:

- virtual QE depth;
- pre-minted escrowed senior buffer;
- internal gradient / signal confidence;
- external trade size, hard capped at 10% of canonical NAV;
- contraction / sterilization intensity;
- route or no-trade.

## Non-negotiable execution gate

External trading is optional.

A trade is allowed only when:

```
expected external edge
>
round-trip DEX fee
+ gas
+ impact
+ safety margin
```

For a symmetric signal:

```
expected edge = (2p-1)*M - C
```

where:

- p = probability direction is correct;
- M = subsequent absolute external move;
- C = full round-trip external cost.

QE can change p only if the internal state contains actual predictive information. QE itself is not revenue.

## Current Base execution context

Research snapshot, September 2026:

- Aerodrome Slipstream WETH/USDC 0.05%: about $10.1m liquidity and ~$21.9m 24h volume.
- Deep Uniswap V3 WETH/USDC 0.30% fallback: about $117m liquidity.

At <=10% of a $100-$500 NAV, market impact is negligible relative to fee/gas.

## Break-even hit-rate frontier

For a $10 round trip using a 5 bp external route and $0.002 gas per leg, approximate total cost is 14 bp.

Therefore:

```
expected move 0.25% -> hit rate > 78%
expected move 0.50% -> hit rate > 64%
expected move 1.00% -> hit rate > 57%
expected move 2.00% -> hit rate > 53.5%
```

This is the core profitability condition for owner-only V17.

## What is required to double NAV

With one accepted external trade per block and trade notional fixed at 10% of current NAV:

```
50 blocks   -> ~13.96% net edge per traded notional
500 blocks  -> ~1.387% net edge per traded notional
5000 blocks -> ~0.1386% net edge per traded notional
```

So +100% in 50 blocks is not credible from ordinary owner-only market making under the 10% cap unless there is an extraordinary external edge.

The 5000-block horizon is much more interesting.

## Immediate scenario frontier

These are deterministic expected-value scenarios, not forecasts.

### Good signal
```
p = 65%
move = 1%
opportunity every block
5bp route
```

Approximate result:

```
50 blocks   -> NAV ~$100.8
500 blocks  -> NAV ~$108.4
5000 blocks -> NAV ~$237
```

### Strong signal
```
p = 70%
move = 1%
opportunity every block
```

Approximate:

```
50 blocks   -> ~$101.3
500 blocks  -> ~$114
5000 blocks -> ~$402
```

### Rare strong signal
```
p = 70%
move = 1%
opportunity on ~25% of blocks
```

Approximate:

```
50 blocks   -> ~$100.3
500 blocks  -> ~$103.3
5000 blocks -> ~$139
```

The important variable is not QE quantity. It is predictive external edge multiplied by opportunity frequency.

## Monetary mechanics retained from V16

### Virtual QE
Unlimited relative to $100 if desired, because it remains internal and non-redeemable.

### Escrowed senior buffer
Pre-minted liquidity held entirely inside owned contracts. It is not circulating liability until released.

### Circulating senior
Counted fully in HF and must remain backed.

### Contraction
When risk rises, V17 first sterilizes virtual QE, then trims escrow, then reduces external risk. It does not manufacture apparent profit by burning one owned token against another.

## Production objective

The controller should optimize:

```
expected external alpha * probability of fill
- external execution cost
- inventory risk
```

subject to:

```
HF target >= 180%
HF hard floor >= 150%
external trade <= 10% canonical NAV
QE excluded from NAV
escrow excluded from circulating debt until released
internal self-fees = 0 consolidated profit
no trade if expected edge <= cost + safety margin
```

## Next real-data gate

Feed the V14 historical Base WETH/USDC block series into V17 and measure p, M and opportunity frequency OOS. If the real OOS signal does not clear the frontier above, the controller stays idle rather than paying the external pool.
