# V10 — Target: +100% canonical NAV in 50 Base blocks

## Non-negotiable definition of success

Start:

```
A0 = $100 canonical assets
L0 = $50 senior redeemable liabilities
HF0 = 200%
```

Success at block 50:

```
A50 >= $200
HF50 >= 180%
LP fair NAV not impaired
qUSDS/qETHS are NOT counted in A
internal-transfer PnL is NOT counted as canonical profit
```

QE may recharge virtual/junior AMM reserves, but it cannot satisfy the +100% target unless real canonical revenue enters the system.

## $10 working size

Each elementary rotation initially uses:

```
u = 10% of NAV = $10
```

If one rotation is allowed per block, compounding requires:

```
(1 + 0.10*m)^50 >= 2
```

so:

```
m >= 13.9595% net per traded notional
```

This is far above normal DEX/bridge fee economics.

## Turnover solution

Allow K rotations of the same inventory per block.

Target equation:

```
(1 + 0.10*m)^(50*K) >= 2
```

Required net margin:

| rotations/block | required net margin |
|---:|---:|
| 1 | 13.9595% |
| 2 | 6.9556% |
| 5 | 2.7764% |
| 10 | 1.3873% |
| 20 | 0.6934% |
| 50 | 0.2773% |
| 100 | 0.1386% |

## V9 bridge-fee example

With:

```
bridge fee              = 20 bp on gross external/user flow
net settlement ratio    = 10%
external DEX fee        = 30 bp on only the 10% residual
gas allocation          = 1 bp of gross flow
```

net margin on gross volume is:

```
20 - 0.10*30 - 1 = 16 bp
```

At 16 bp, required turnover is approximately:

```
86.65 rotations/block
```

Use 87 in the discrete simulator.

Starting with $100 and reinvesting each rotation:

```
50 blocks
87 rotations/block
10% NAV per rotation
16 bp net canonical margin

final NAV    ~= $200.56
profit       ~= $100.56
ROI          ~= +100.56%
gross volume ~= $62,850
```

The large Base WETH/USDC pool is deep enough in TVL terms for this gross notional. The difficult assumption is not liquidity depth; it is obtaining genuine external/user flow or genuine external alpha at 16 bp net for thousands of rotations.

## QE role

QE is an internal accelerator:

```
QE mint qUSDS/qETHS
 -> restores virtual gradient/inventory depth
 -> improves routing and internal netting
 -> reduces external settlement ratio
 -> reduces fees/slippage/gas per gross volume
```

QE does NOT directly increase canonical NAV.

Only retained canonical revenue can be converted into new senior redeemable inventory:

```
safe seniorization <= retained canonical revenue / targetHF
```

## Optimization objective

Primary:

```
maximize A50
```

Secondary:

```
minimize:
- external settlement ratio
- gas / gross volume
- senior inventory consumption
- adverse selection
- number of external swaps
```

Subject to:

```
A50 >= 200
HF >= 180% target
HF never < 150%
LP fair NAV protected
senior mint canonically funded
q-assets non-redeemable by default
owner payout disabled until A >= 200
```

## Search variables

- rotations per block K
- utilization per rotation u <= 10%
- bridge fee by inventory direction
- net-settlement ratio
- QE target gradient/corridor
- qUSDS/qETHS virtual depth
- number of bridge pools
- routing path
- batching size
- minimum execution edge
- reverse-QE seniorization rate
- owner payout after target is reached

## Acceptance tests

A candidate configuration is accepted only if:

1. canonical NAV doubles in <=50 blocks in the scenario;
2. at least 100 randomized flow/order permutations also keep HF above the hard floor;
3. removing external/user fee income causes the target to fail — proving QE alone is not fabricating profit;
4. qUSDS/qETHS cannot be redeemed 1:1 through the bridge;
5. no internal transfer is counted as external revenue;
6. all DEX fees, gas and residual settlement costs are charged;
7. Base fork execution matches the Python accounting within tolerance.

## Key research target

The most important quantity is:

```
turnover efficiency = gross external/user volume / required canonical capital
```

The +100%/50-block target becomes feasible only if capital can be reused many times while real external flow supplies a small positive canonical margin each rotation.
