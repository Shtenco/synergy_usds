# V19 — ORIGINAL QE ARBITRAGE LOOP

This version explicitly restores the original concept.

## Objective

The protocol owns:

- the internal fork ETHS/USDS pool;
- the USDC/USDS bridge pool;
- the WETH/ETHS bridge pool;
- the QE/printing controller;
- the arbitrage executor.

The only third-party liquidity is the very large Base Mainnet external WETH/USDC pool.

The intended perpetual loop is:

```
QE / PRINT
    ↓
Recharge controlled fork gradient
    ↓
Fork ETHS/USDS price diverges from Base
    ↓
Arbitrage executor detects the direction
    ↓
Trade against foreign Base WETH/USDC pool
    ↓
Close the synthetic legs through pool bridges
    ↓
Bridge inventories become skewed
    ↓
Net / rebalance bridge pools
    ↓
Sterilize excess virtual QE
    ↓
Recharge the next gradient
```

## Two directions

### Cycle A — internal ETHS expensive

```
USDC
→ buy WETH on Base
→ WETH/ETHS pool bridge
→ ETHS
→ sell ETHS in fork pool
→ USDS
→ USDS/USDC pool bridge
→ USDC
```

The arbitrage executor sees:

```
P_fork(ETHS) > P_base(WETH) + full route cost
```

### Cycle B — internal ETHS cheap

```
USDC
→ USDC/USDS pool bridge
→ USDS
→ buy ETHS in fork pool
→ ETHS/WETH pool bridge
→ WETH
→ sell WETH on Base
→ USDC
```

Triggered when:

```
P_fork(ETHS) < P_base(WETH) - full route cost
```

## QE recharge

QE controls **virtual** reserves:

```
qUSDS
qETHS
```

These alter the internal pricing curve and can recharge the target gradient.

They are not automatically redeemable through the bridge.

The bridge can only settle the **senior** component that is covered by its protocol-owned inventory / canonical reserves.

Thus:

```
virtual QE can be huge
senior bridge settlement is inventory bounded
```

This preserves the original money-printer mechanic without pretending that every printed unit is a claim on USDC.

## Pool bridges, not only lock/mint

The two bridges are treated as protocol-owned liquidity pools:

```
BridgeUSD: USDC <-> senior USDS
BridgeETH: WETH <-> senior ETHS
```

They have:

- canonical inventory;
- synthetic senior inventory;
- target inventory bands;
- skew-sensitive pricing;
- pool fees;
- netting across Cycle A / Cycle B;
- emergency canonical reserve floors.

The arbitrage loop therefore closes through liquidity pools, exactly as in the original architecture.

## Why alternating directions matter

A permanent one-way gradient drains one bridge inventory.

A perpetual controller should therefore optimize:

```
gradient direction
gradient magnitude
trade size
bridge skew
QE recharge
```

so that profitable cycles also keep the bridge inventories oscillating around target.

The intended state machine is:

```
bridge USDC low
→ favor Cycle B
→ USDC returns to bridge side

bridge WETH low
→ favor Cycle A/B according to which side repairs WETH inventory

balanced bridges
→ choose the larger arbitrage spread
```

## Accounting

V19 deliberately reports **both**:

1. `arb_executor_pnl` — what the arbitrage contract earns on the route;
2. `consolidated_canonical_nav` — what the whole protocol owns in USDC/WETH.

This is essential because all internal pools are protocol-owned.

A cycle can show positive executor PnL while another owned pool loses the same value.

That does not invalidate the mechanism, but it tells us whether QE is:

- merely circulating value internally, or
- actually increasing canonical protocol capital.

## Main optimization target

The original mechanism is preserved, but the optimizer has two objectives:

```
MAX cumulative arb_executor_pnl
```

subject to:

```
bridge reserves never exhausted
HF >= floor
senior settlement fully covered
```

and, separately:

```
MAX Delta consolidated_canonical_nav
```

This lets us distinguish "money printer throughput" from actual external wealth creation.

## Next experiment

Start from:

```
total protocol capital = $100
$50 fork / synthetic side
$50 Base / canonical side
external leg <= $10 per cycle
```

Run 50 blocks with a controller that can choose each block:

- Cycle A;
- Cycle B;
- no trade;
- QE qUSDS;
- QE qETHS;
- bridge-pool rebalance;
- sterilization.

The controller should maximize arb throughput while keeping both bridge pools alive and report the consolidated NAV separately.
