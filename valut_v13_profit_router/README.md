# V13 — Profit-Maximizing Per-Order Router

## What K means

K is the expected number of **external paid incoming orders per Base block**.

Example:

```
K = 200
mean order ~= $10
potential gross demand ~= $2,000/block
```

Actual accepted volume is lower because order sizes vary, bridge fees reduce fill probability, QE throughput is capped, and some orders may be rejected.

K is never protocol self-trading.

## Architecture

```
Foreign deep Base WETH/USDC venues
                 ^
                 |
        residual settlement only
                 |
Bridge hot inventory / netting pool
                 ^
                 |
Fork senior ETHS/USDS pool
                 ^
                 |
QE junior/virtual reserve
```

QE recharges virtual depth and gradient but cannot satisfy an uncovered senior redemption by itself.

## Per-order routing priority

For every incoming ~$10-class order V13 evaluates:

1. **Internal net** — use an opposite flow already on the bridge.
2. **Hot inventory** — use pre-funded senior bridge inventory while inside the risk band.
3. **Split route** — retain only the profitable inventory amount and externally settle the residual.
4. **External route selection** — choose the cheapest available real Base venue.

The order is charged a bridge fee. The canonical profit is:

```
bridge fee revenue
- external DEX fee
- depth/slippage proxy
- gas
- adverse-selection cost
```

Internal QE mint is never included.

## Fee result

The V12 idea of large surcharges on imbalance-worsening flow was not optimal in the current demand model because it suppressed too much paid volume.

V13's best simple policy in the eta~=0.02 scenario is approximately:

```
base fee ~= 60 bp
healing discount up to 10 bp
no mandatory extra harmful-flow surcharge
```

The reason is economic: retain high order fill while making inventory-healing flow slightly more attractive.

## Monte-Carlo checkpoints

Scenario results, not market forecasts:

### K = 150
```
median final canonical NAV ~= $263.6
p05                         ~= $256.5
mean gross accepted flow    ~= $28.75k
mean external settlement    ~= $6.16k
mean canonical costs        ~= $2.13
```

### K = 200
```
median final canonical NAV ~= $318.3
p05                         ~= $307.6
p95                         ~= $330.3
success rate                = 100% in 300 scenario trials

mean gross accepted flow    ~= $38.33k
mean external settlement    ~= $8.33k
mean fee revenue            ~= $221.37
mean canonical costs        ~= $2.84
```

### K = 250
```
median final canonical NAV ~= $374.1
p05                         ~= $361.2
p95                         ~= $385.8

mean gross accepted flow    ~= $48.03k
mean external settlement    ~= $10.36k
mean fee revenue            ~= $277.34
mean canonical costs        ~= $3.52
```

The router therefore routes roughly 75-80% of accepted notional through internal netting/hot inventory and only the residual to external venues in this scenario.

## Current deep external fallback

Uniswap V3 WETH/USDC 0.30% on Base:

`0x6c561b446416e1a00e8e93e221854d6ea4171372`

Current research snapshot around September 2026: roughly $128.6m liquidity and ~$81.6m 24h volume.

Cheaper routes such as Aerodrome Slipstream 5bp and Pancake V3 1bp are preferred when available; the very deep Uniswap pool is the reliable fallback.

## Safety interpretation

The router maximizes canonical revenue per order, but it may not:

- count qUSDS/qETHS as canonical assets;
- use QE to cover senior redemptions without backing;
- count protocol self-trades as external fee revenue;
- ignore external settlement costs.

Thus the original three-pool concept is preserved, while the router chooses the least expensive real settlement path for each external order.
