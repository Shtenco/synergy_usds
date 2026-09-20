# V12 — Adaptive Fee + QE Controller for the original 3-layer scheme

## Original architecture preserved

```
Foreign deep Base WETH/USDC pool
              <-> 
Bridge / netting pool
              <->
Internal fork ETHS/USDS pool
              <->
QE virtual/junior reserve
```

The current deep Base execution anchor remains Uniswap V3 WETH/USDC 0.30% pool
`0x6c561b446416e1a00e8e93e221854d6ea4171372`, recently observed around $118m-$129m liquidity.

At $10-class legs, external price impact is negligible relative to fees. The controller therefore focuses on fee capture, inventory netting and minimizing residual settlement.

## Controller

Every block V12 updates:

1. estimated demand elasticity eta;
2. revenue-maximizing base bridge fee;
3. lower fee for inventory-healing flow;
4. surcharge for inventory-worsening flow;
5. QE virtual throughput;
6. hot inventory band;
7. residual external settlement.

For the demand model:

```
fill_probability(f) = exp(-eta * (f - reference_fee))
```

the fee-only revenue optimum is approximately:

```
f* = reference_fee + 1/eta
```

The controller estimates eta from quote/fill observations with an EWMA and moves the base fee toward this point.

## Directional pricing

If bridge inventory is long in one direction:

```
flow that worsens skew -> base fee + surcharge
flow that heals skew    -> base fee - discount
```

This causes external users to perform part of the rebalance and reduces the amount that must touch the foreign pool.

## QE role

QE raises internal virtual/junior throughput:

```
qe_capacity = 1.2 * requested gross flow
```

bounded in the research model to $500-$2,500 per block.

QE is never added to canonical assets and qUSDS/qETHS remain non-redeemable by default.

## Scenario results

These are model results, not forecasts.

At true demand elasticity eta = 0.02 and 150 potential $10-class paid flows per block:

### fixed 35 bp
Approximate 50-block Monte Carlo:
- median canonical assets: ~$254
- p05: ~$248
- gross accepted flow: ~$45.5k
- external settlement: ~$9.2k

### adaptive directional controller
Depending on the learned fee level:
- median canonical assets: about $263-$266
- p05: about $256-$259
- external settlement falls to roughly $4-$5k

The largest gain is reduced external settlement, not fabricated QE profit.

## Higher real flow

With the same eta=0.02 scenario and adaptive controller:

```
K=180 -> median ~ $295
K=200 -> median ~ $317, p05 ~ $307
K=220 -> median ~ $338
K=250 -> median ~ $371, p05 ~ $359
```

K means exogenous paid $10-class flows per block. It is NOT protocol self-trading.

Therefore profit continues to scale while the $100 balance sheet can recycle inventory, but only if genuine external flow exists.

## Critical upper-bound interpretation

The very large Base pool removes external depth as the first-order constraint at these sizes.

The limiting resources become:

- paid user/order flow;
- demand elasticity to bridge fees;
- senior inventory;
- inventory netting ratio;
- QE throughput;
- gas batching;
- route availability.

Self-generated rotations cannot be counted as fee revenue because both sides belong to the protocol.

## Production objective

Maximize:

```
canonical fee/alpha revenue - external settlement cost
```

subject to:

```
HF >= 150% hard floor
QE assets excluded from canonical NAV
q-assets non-redeemable
senior liabilities backed
no self-trade revenue
external pool costs charged
```

## Next production step

Integrate the controller into the BridgeVault/NettingVault so every quote carries:

- direction-specific fee;
- inventory impact;
- QE capacity reservation;
- expected residual settlement;
- minimum canonical edge.

Then replay historical Base block flow before any mainnet deployment.
