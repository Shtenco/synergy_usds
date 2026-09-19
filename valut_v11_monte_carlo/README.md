# V11 — Monte Carlo + Base fork

## Goal

Start with exactly $100 canonical capital and $50 senior liabilities. A run succeeds only if after 50 blocks:

- canonical assets >= $200;
- hard HF never falls below 150%;
- qUSDS/qETHS are not counted as canonical assets;
- internal transfer PnL is not counted as revenue;
- all external settlement fees, slippage proxy, batching gas and modeled operational losses are charged.

The optimizer searches K=50..150 external $10-class user flows per block, bridge fees, QE virtual throughput, inventory bands and 8 Base routing venues.

## Flow model

K is external paid flow/capacity, not self-trading. Per block:

1. random order sizes are centered around $10;
2. directions have correlated random imbalance;
3. opposite directions are netted;
4. QE maintains virtual/junior internal depth up to its throughput cap;
5. canonical settlement is only the residual inventory imbalance;
6. the router chooses the cheapest currently available Base venue;
7. bridge fee is charged on gross user flow;
8. DEX fee/gas/adverse-selection cost is charged only on residual external settlement.

QE never enters canonical NAV directly.

## Current Base route registry

1. Pancake V3 WETH/USDC 0.01% — 0x72ab388e2e2f6facef59e3c3fa2c4e29011c2d38
2. Aerodrome Slipstream WETH/USDC 0.05% — 0xb2cc224c1c9fee385f8ad6a55b4d94e92359dc59
3. Aerodrome Slipstream3 WETH/USDC 0.05% — 0x3fe04a59ebd38cf06080a6f60a98d124eb59392a
4. Uniswap V3 WETH/USDC 0.30% — 0x6c561b446416e1a00e8e93e221854d6ea4171372
5. Aerodrome Slipstream WETH/USDC 0.01% — 0xdbc6998296caa1652a810dc8d3baf4a8294330f1
6. Sushiswap V3 WETH/USDC 0.30% — 0x41595326aabe6132fc6c7ae71af087a3a9dbc9f6
7. Uniswap V3 WETH/USDC 0.03% — 0x18b497f71122622557e4634c47a05647ff859f47
8. Aerodrome WETH/USDC — 0x3548029694fbb241d45fb24ba0cd9c9d4e745f16

Liquidity figures are research snapshots and must be refreshed before deployment.

## 1000-trial checkpoints from the research model

Under the V11 scenario assumptions:

### Low-fee / maximum-throughput

- bridge fee: 15 bp
- K: 150
- QE capacity: $2,000 virtual throughput/block
- median final canonical assets: about $208.3
- 5th percentile: about $205.8
- mean gross user flow: about $75.0k / 50 blocks

### Lower-throughput target configuration

- bridge fee: 20 bp
- K: 110
- QE capacity: $1,500 virtual throughput/block
- median final canonical assets: about $206.8
- 5th percentile: about $204.4
- mean gross user flow: about $55.0k / 50 blocks
- mean external settlement: about $11.1k
- mean total modeled execution/shock cost: about $3.16

### Maximum-NAV configuration in the initial restricted search

- bridge fee: 35 bp
- K: 150
- QE capacity: $2,000 virtual throughput/block
- median final canonical assets: about $315.7
- 5th percentile: about $311.2
- mean gross flow: about $62.6k

A wider fee-elasticity sensitivity search can prefer much higher bridge fees. That result is demand-model dependent and must not be treated as a market prediction.

## Key interpretation

The +100% result is only possible because tens of thousands of dollars of exogenous paid flow are processed using a $100 balance sheet while opposite flows are netted. QE increases internal throughput but does not create the profit.

If fee income is removed, the target must fail. This is an explicit unit test.

## Run

```bash
cd valut_v11_monte_carlo/model
python3 -m unittest -v test_v11.py
python3 monte_carlo_v11.py --trials 200 --out v11_grid.csv
```

## Base fork

```bash
cd valut_v11_monte_carlo
BASE_RPC_URL=https://mainnet.base.org forge test -vvv
```

The fork harness verifies that all registered pool contracts exist on Base and that the deep Uniswap WETH/USDC pool has large live token balances. The V6 fork test remains the execution-level Aerodrome swap harness.
