# V15 — Owner-Only QE Signal Optimizer

This version preserves the V14 consolidated ownership model.

The protocol owns the fork pool, bridge pool, QE engine and arbitrage contract. Only trades against foreign Base liquidity may change group-level canonical PnL.

## Immediate null result

For a flat external market, 50 external $10 trades through a 30 bp foreign pool with $0.002 gas per trade:

```
cost per trade = $10*0.30% + $0.002 = $0.032
50 trades       = $1.60
final NAV       = $98.40
```

At the same time an internal 16.4x QE accounting loop could report:

```
50 * (16.4-1) * $10 = $7,700
```

but this amount is excluded from consolidated canonical NAV.

Therefore permanent gradient recharge has no standalone profit source.

## External move required to beat round-trip cost

Approximate round-trip break-even for a $10 trade with $0.002 gas each leg:

```
30 bp venue -> 0.64%
 5 bp venue -> 0.14%
 1 bp venue -> 0.06%
```

Any QE-derived trading signal must forecast enough subsequent external price movement to clear this cost.

## Optimization variables

V15 searches:

- signal: momentum / mean reversion / external flow / hybrid;
- lookback: 1,2,3,5,8,13,21 blocks;
- holding period: 1,2,3,5,8,13 blocks;
- external trade size: $2.5,$5,$7.5,$10;
- signal threshold.

The objective is OOS consolidated canonical NAV relative to the passive $50 USDC + $50 WETH benchmark.

## Anti-overfit

70% train / 30% OOS plus optional rolling walk-forward.

A configuration is accepted only if:

```
OOS NAV(strategy) > OOS NAV(passive hold)
```

after foreign-pool fee and gas.

Internal QE PnL is never part of the objective.

## Why this matters

If V15 finds no robust OOS alpha, the owner-only three-contract loop cannot become profitable merely by recharging the fork gradient.

If V15 does find robust OOS alpha, the economic source of profit is external market predictability, while QE acts as the control/inventory mechanism.
