# V9 — $10 cycles + QE fork pool + bridge-pool ring

## Current Base external anchor

Working external WETH/USDC venue:

- Uniswap V3 Base
- fee: 0.3%
- pool: `0x6c561B446416E1A00E8E93E221854d6eA4171372`
- WETH: `0x4200000000000000000000000000000000000006`
- USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- observed liquidity around $118m-$129m in September 2026

For a $10 external leg:

```
10 / 128,614,644.53 = 0.00000007775
                     = 0.000007775% of TVL
```

So depth is effectively enormous relative to the protocol. It is not literally infinite: fee tiers, active Uniswap V3 liquidity, MEV and market movement still matter.

## V9 trade size

```
Initial real capital = $100
External leg / cycle = $10
Trade fraction        = 10% of initial capital
```

## Why senior QE cannot be perpetual

With fork LP fair NAV $50 and the old 16.4x target gradient, a $10 external purchase followed by ETHS sale produces approximately:

```
senior USDS output on first cycle ~= $36.56
full price-reset requirement       ~= $200.07 USDS
```

If the reset mint is senior 1:1 redeemable USDS, liabilities explode immediately. A $128m external pool does not fix that because the value loss is inside the fork/bridge balance sheet.

## V9 solution: two-layer QE

Separate:

```
SENIOR:
USDS / ETHS
canonically backed
bridge redeemable

JUNIOR QE:
qUSDS / qETHS or virtual reserves
internal pricing/inventory only
NOT automatically redeemable through the bridge
```

QE can recharge the internal pricing curve by adding junior/virtual reserves without creating senior bridge debt.

The AMM prices against:

```
total reserve = senior reserve + QE virtual reserve
```

but swap output is split between senior and junior components. Only senior output is eligible for canonical redemption.

This means the gradient can be maintained indefinitely as an internal routing mechanism, while canonical extraction remains bounded by real senior inventory and real external revenue.

## What the first cycles show

At 16.4x and $10/cycle the first cycle removes most of the senior USDS side. After the QE reset, later outputs increasingly consist of qUSDS rather than redeemable USDS.

This is intentional. If QE-created output were fully redeemable, QE would simply be bridge debt.

## Bridge-pool ring

Use several bridge/inventory pools:

```
Base WETH/USDC external venue
        <->
Base hot inventory
        <->
Bridge Netting Vault
        <->
Fork senior ETHS/USDS pool
        <->
Fork QE virtual/junior pool
        <->
Reverse-QE / sterilization vault
```

Opposite flows are netted before external settlement.

Example for each $10 gross unit:

```
gross bridge flow       = $10
90% matched internally  = $9
external residual       = $1
```

At the 0.3% Uniswap fee tier:

```
external fee ~= $0.003
```

instead of $0.03 if the whole $10 were externally settled.

## Example fee economics

Scenario only:

```
gross volume            = $10
bridge fee              = 20 bp = $0.020
net settlement ratio    = 10%
external fee on $1      = $0.003
batched gas allocation  = $0.001

net canonical revenue   = $0.016 / cycle
```

With 40/60:

```
owner                    = $0.0064 / cycle
retained reserve         = $0.0096 / cycle
```

After 10,000 such externally-funded flow epochs:

```
owner cumulative         ~= $64
canonical assets         ~= $196
senior liabilities       = $50
HF                       ~= 392%
```

This is a deterministic scenario, not a forecast. It requires real external/user volume paying the bridge fee.

## Safe conversion of QE into senior inventory

At target HF h:

```
B = A - hL
```

If new retained canonical revenue is R, the maximum new senior liability that can be minted without reducing B is:

```
Delta L <= R / h
```

At h=1.80 and retained revenue $0.0096:

```
safe senior recharge <= $0.00533
```

per cycle.

QE itself can be much larger because QE reserves are junior/non-redeemable.

## Reverse QE / sterilization

When real fee revenue accumulates:

1. canonical revenue enters treasury;
2. target HF is restored first;
3. a bounded amount can back new senior inventory;
4. excess qUSDS/qETHS is burned;
5. bridge pools are rebalanced;
6. only then can owner payout occur.

Thus:

```
QE creates internal virtual liquidity
External revenue creates canonical equity
Reverse-QE converts only funded headroom into senior liquidity
```

## Important bottleneck

For $10 trades the >$100m Base pool is not the bottleneck.

The bottlenecks are:

- senior fork inventory;
- bridge backing;
- opposite user flow available for netting;
- fees/gas;
- QE sterilization rate.

The external pool is effectively deep enough that these dominate the economics.
