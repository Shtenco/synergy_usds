# V20 — Closed-Loop QE Inventory Engine

V20 answers one question:

> Can QE -> fork arbitrage -> pool bridges -> Base -> reverse cycle -> restored bridge inventories leave the protocol with more canonical USDC/WETH than it started with?

## Ownership

The protocol owns all internal components:

- fork ETHS/USDS AMM;
- USDC/USDS bridge pool;
- WETH/ETHS bridge pool;
- QE controller;
- arbitrage executor.

Only the large Base WETH/USDC pool is external.

## Hard closure condition

A candidate cycle is only considered closed when:

- the synthetic bridge legs are netted/sterilized;
- fork and bridge accounting is returned to its starting target;
- no qUSDS/qETHS is counted as canonical assets;
- the final result is marked using the same external WETH price as the start.

Under these conditions every internal payment cancels on consolidation.

The only remaining external cash flow is the protocol's BUY/SELL against the foreign AMM.

## Exact CPMM test

External pool approximation:

```
TVL = $118m
price = $2,500/WETH
external notional = $10
```

A complete A+B loop uses the real x*y=k external-pool equations.

Before gas:

```
1 bp route  -> about -$0.0020 per $10 round trip
5 bp route  -> about -$0.0100
30 bp route -> about -$0.0599
```

With $0.002 gas per external leg:

```
1 bp route -> about -$0.0060 per full loop
```

50 identical closed loops:

```
start canonical NAV = $100
final canonical NAV ~= $99.70
```

## The gradient paradox

The internal arbitrage executor can report arbitrarily large profit as QE gradient grows.

For 50 $10 A+B loops on the 1 bp route:

```
gradient 1.01x  -> executor transfer PnL ~ $10
gradient 1.10x  -> ~ $100
gradient 2x     -> ~ $1,000
gradient 16.4x  -> ~ $15,400
gradient 100x   -> ~ $99,000
```

Yet consolidated canonical NAV remains approximately:

```
$99.70
```

in every case.

Reason: the executor's gain is the fork/bridge pool's internal loss. Both are owned by the same protocol.

## Exhaustive parameter search

V20 searches:

- external fee: 1 / 5 / 30 bp;
- QE gradients: 1.01x ... 100x;
- trade sizes: $0.10 ... $10.

With the external price unchanged and the internal inventories returned to target, no positive canonical closed loop is found.

The best canonical action is therefore "do nothing"; among nonzero trades the smallest possible trade loses the least.

## What must be added for a genuinely profitable closed loop

At least one net external value source must enter between A and B:

1. **external price movement** while the protocol holds WETH;
2. **cross-DEX external mispricing**, so one foreign pool sells cheaper than another buys;
3. **external users paying fees** into a protocol-owned bridge/fork pool;
4. **external yield/incentives** earned by canonical reserves;
5. another non-protocol counterparty willingly accepting the newly issued synthetic asset.

Without one of these, the closed system cannot create canonical USDC/WETH from its own internal QE.

## Closest version to the original concept

The original loop itself remains useful:

```
QE
-> gradient
-> arbitrage executor
-> pool bridges
-> reverse gradient
-> reverse arbitrage
-> restored inventory
```

But V20 shows exactly what the next design has to accomplish:

```
external value captured during the A/B loop
>
external fees + gas
```

The most faithful next extension is not to remove QE. It is to keep the QE loop and add an **external-capture leg** inside each closed A+B cycle, while bridge inventories are still returned to their initial state.
