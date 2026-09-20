# V14 — Owner-Only Consolidated Replay

## Ownership assumption

The protocol owns 100% of:

- the internal fork ETHS/USDS pool;
- the bridge/netting pool;
- the QE controller;
- the arbitrage contract;
- all senior/junior internal inventory.

The only third-party capital is in the foreign Base WETH/USDC pool.

This changes the accounting completely.

## Consolidation rule

All protocol-owned contracts are treated as one balance sheet.

Therefore:

```
fee paid by own arb bot -> own bridge pool = internal transfer = $0 group profit
QE mint inside fork = internal accounting = $0 canonical profit
USDS/ETHS movement between own contracts = internal transfer = $0 group profit
```

The only canonical group PnL comes from changes in externally held/settled USDC and WETH after interacting with the foreign pool.

## Key economic identity

The original cycle:

```
own USDC
-> buy WETH in foreign pool
-> own bridge lock/mint
-> own fork pool swap
-> own bridge redeem
-> own arb contract
```

consolidates to:

```
own USDC -> WETH in the foreign pool
```

Everything after the external swap is inside the same owner group.

The reverse cycle consolidates to:

```
own WETH -> USDC in the foreign pool
```

So an artificial fork gradient is a routing/signal mechanism, not a free source of system-level value.

## What QE can still do

QE can:

- restore internal virtual depth;
- change the internal shadow price;
- move inventory among own contracts;
- determine when the arbitrage contract buys or sells externally.

But QE cannot increase consolidated canonical NAV merely by minting qUSDS/qETHS.

If the QE gradient has no predictive relationship to future foreign-pool price movement, repeated external round trips lose DEX fees and gas.

## Historical Base replay

`fetch_base_swaps.py` downloads real Swap logs from the deep Base Uniswap V3 WETH/USDC pool:

`0x6c561b446416e1a00e8e93e221854d6ea4171372`

using the standard Uniswap V3 Swap topic:

`0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67`

It reconstructs:

- real block-by-block WETH/USDC close price;
- swap count;
- WETH volume;
- USDC volume;
- net pool USDC flow.

The replay then tests the protocol against the real external price path.

## Replay modes

### 1. no_trade

Benchmark. Own $100 balance sheet simply holds the initial $50 USDC + $50 WETH-equivalent.

### 2. alternating

Pure artificial QE gradient: buy external WETH one block, sell it the next.

This is the clean test of whether "recharging the gradient" creates consolidated profit by itself.

On a flat synthetic price path the unit test requires this strategy to lose money because external DEX fee + gas are real costs.

### 3. random

Random QE direction. Useful as another null hypothesis.

### 4. momentum / mean_reversion

The QE gradient direction is driven by historical foreign-pool price data.

If these make money, that profit is classified as external trading alpha, not QE seigniorage.

## Train / OOS

The optimizer uses 70% of the replay window to choose:

- signal family;
- lookback;
- external trade size up to $10.

The remaining ~30% is OOS and is compared against no-trade.

A strategy is not accepted as evidence of profitability unless OOS consolidated canonical NAV beats the benchmark after external fees and gas.

## Fetch

```bash
cd valut_v14_owner_only_replay
python3 fetch_base_swaps.py \
  --rpc https://mainnet.base.org \
  --blocks 500 \
  --out base_weth_usdc_blocks.csv
```

The script queries `eth_getLogs` in small chunks to tolerate public-RPC limits.

## Replay last 50 Base blocks

```bash
python3 owner_only_replay_v14.py base_weth_usdc_blocks.csv \
  --last 50 \
  --json-out v14_result.json
```

## Acceptance criterion

For the owner-only architecture, the economically meaningful test is:

```
Consolidated canonical NAV after external settlement
>
no-trade consolidated canonical NAV
```

after:

- Uniswap fee;
- gas;
- mark-to-market of all owned WETH;
- zero credit for QE mint;
- zero credit for internal self-fees.

This is deliberately stricter than V11-V13 because there is no external user fee flow inside the protocol.
