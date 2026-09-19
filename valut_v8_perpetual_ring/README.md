# V8 — Perpetual Bridge Ring

V7 stays preserved as the capital-release experiment. V8 changes the objective: preserve the original $100 real capital and make active operation non-self-destructive.

## Start

Canonical assets A = $100  
Senior redeemable liabilities L = $50  
HF = A/L = 200%  
Fork LP fair NAV = $50  
Base free/rebalance reserve = $50

The fork display NAV is not added to A a second time.

## Perpetual invariant

Choose target collateralization h = 1.80 and define safety surplus:

```
B = A - h*L
```

For A=$100 and L=$50:

```
B0 = 100 - 1.8*50 = $10
```

Only canonical external revenue can increase distributable profit:

```
R = bridge fees
  + external LP fees
  + genuine cross-venue arbitrage
  + lending/staking/solver revenue
  - gas
  - slippage
  - hedge/rebalance loss
  - bad debt
```

Internal oracle-spread transfer PnL is excluded.

With 40% owner / 60% retained reserve and matched 1:1 liability growth dL:

```
Delta B = 0.60*R - (h-1)*dL
        = 0.60*R - 0.80*dL
```

Therefore non-decaying target surplus requires:

```
R >= 1.333333*dL
```

If liabilities are not growing, any positive net R grows canonical safety surplus.

## Why rebalance can be perpetual

Rebalance does not create value. It reduces cost and capital usage by:

1. netting opposite bridge flows before settlement;
2. reusing inventory instead of minting;
3. routing users to the side that repairs current inventory imbalance;
4. batching residual settlement;
5. charging more to flow that worsens imbalance;
6. discounting flow that repairs imbalance;
7. executing external trades only when the canonical edge safely exceeds all costs.

## Multi-pool ring

```
Base hot settlement reserve
        <-> Base external LP/execution pools
        <-> Bridge netting vault
        <-> Fork ETHS/USDS protocol-owned AMM
        <-> Fork inventory buffer
        <-> back to settlement
```

Example:

```
Base -> Fork flow = $8
Fork -> Base flow = $7
gross bridge volume = $15
actual canonical settlement = $1
```

The $14 matched flow is netted internally; only $1 needs external settlement.

## No forced reset

Production V8 does not restore 12x or 16.4x internal premium.

Use an oracle corridor:

```
P_internal in [P_external*(1-d), P_external*(1+d)]
```

and let ordinary arbitrage close deviations.

The V7 16.4x result remains a stress/capital-release experiment, not a perpetual source of external profit.

## Senior / junior split

Recommended:

- senior USDS/ETHS = canonically backed, 1:1 redeemable;
- junior LP/rebase shares = absorb inventory variance and are not automatic bridge debt.

Zero-loss third-party LP protection can only be paid from canonical reserves or realized external revenue.

## Solvency state machine

```
HF >= 200%:
    normal execution
    up to 40% of NEW external net revenue may go to owner

180% <= HF < 200%:
    no capital-release payout
    revenue repairs reserve first

170% <= HF < 180%:
    defensive mode
    100% revenue retained
    only inventory-repairing trades

150% <= HF < 170%:
    recovery mode
    stop expansion and owner payouts

HF < 150%:
    emergency pause
    redemption/settlement only
```

## Execution gate

Before any rebalance:

```
expected canonical revenue >= safety_multiplier * all execution costs
```

V8 uses 1.25x in the model.

If not satisfied, do nothing.

## Break-even examples

If fixed cost per epoch is $0.002:

```
5 bp net variable margin  -> minimum volume ~= $4
10 bp net variable margin -> minimum volume ~= $2
20 bp net variable margin -> minimum volume ~= $1
```

## 10,000-epoch deterministic demo

Scenario assumptions only:

- $5 external/user volume per epoch
- 15 bp gross external canonical edge
- 5 bp variable leakage
- $0.002 fixed cost
- no liability growth

Net external revenue = $0.003/epoch.

With 40/60:

```
owner   = $0.0012/epoch
reserve = $0.0018/epoch
```

After 10,000 epochs:

```
owner cumulative ~= $12
canonical assets ~= $118
liabilities      = $50
HF               ~= 236%
```

This is not a profit forecast. It demonstrates the accounting property that, with positive realized external net revenue and no internal-transfer PnL misclassified as profit, safety surplus grows.

## Production objective

Do not optimize bot PnL.

Optimize:

```
Delta canonical safety surplus / gas
```

subject to:

```
HF >= hard floor
LP protection is actually funded
senior mint is backed
owner payout comes only from new canonical external revenue
no trade is mandatory
```

Under bounded market and contract risk, this architecture can operate indefinitely. It is not a literal guarantee against arbitrary hacks, oracle failure, stablecoin failure, or unbounded market shocks.
