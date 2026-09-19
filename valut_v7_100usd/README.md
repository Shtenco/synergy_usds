# V7 — $100 bootstrap: $50 fork + $50 Base

## Strict interpretation of the $100 start

The fork-side $50 synthetic LP position is not counted twice.

Economic setup:

- $100 real canonical capital exists.
- $50 backs the synthetic position represented on the fork.
- $50 is additional Base reserve.
- fork displayed fair NAV = $50.
- redeemable synthetic liabilities = $50.
- canonical assets = $100.
- starting HF = 200%.

If one counted the $50 synthetic position as an additional real asset, the same collateral would be counted twice.

## Main V7 change: NAV-only rebase

V6 restored the full artificial internal price after each arbitrage. That is very expensive because:

```
full_reset_mint ≈ target_price * q + USDS_out
```

For a small trade this is roughly twice the sale side.

V7 instead restores only the LP fair NAV at the external fair price:

```
nav_rebase = max(0, LP_NAV_before - LP_NAV_after_trade)
```

The LP remains whole in fair-value terms, while the internal premium is allowed to decay naturally toward the external market.

## Baseline comparison

Assumptions used only for the comparative simulation:

- external ETH price: $2,500
- external CPMM TVL approximation: $118M
- external fee: 5 bp
- internal fee: 30 bp
- initial internal premium: 12x
- trade size: 1.25% of current ETHS reserve
- execution+gas assumption: $0.002/cycle
- HF floor: 150%

### Old full reset + 40/30/20/10

```
cycles                 ≈ 20
owner cash-out         ≈ $4.68
gross bot PnL          ≈ $11.69
HF                     ≈ 149.55% -> stop
internal price         = $30,000 (forced)
LP fair NAV            grows artificially because reset overcompensates it
```

### V7 NAV rebase + original 40/30/20/10

```
cycles                 ≈ 150
owner cash-out         ≈ $20.18
gross bot PnL          ≈ $50.44
external execution cost≈ $0.31
HF                     = 150%
LP fair NAV            = $50.00
internal price         ≈ $2,542
```

### V7 bootstrap waterfall: 40% owner / 60% bridge reserve

At only $100 initial capital, separate insurance and buyback buckets are too small to justify idling capital. During bootstrap, recycle all non-owner flow into the bridge.

```
cycles                 ≈ 150
owner cash-out         ≈ $20.18
bridge assets          ≈ $79.51
liabilities            ≈ $50.00
HF                     ≈ 159.03%
LP fair NAV            = $50.00
internal price         ≈ $2,542
```

The owner receives the same amount as in 40/30/20/10, but the bridge ends with materially more solvency headroom.

## Grid-search bootstrap point

Under the same simplified fee/gas assumptions, the capital-release optimizer finds approximately:

```
internal premium       ≈ 16.4x
trade fraction         ≈ 4.4% of ETHS reserve
cycles                 ≈ 50
gross transfer PnL     ≈ $62.19
owner cash-out @40%    ≈ $24.88
external costs         ≈ $0.11
bridge assets          ≈ $75.01
liabilities            = $50.00
HF                     ≈ 150.02%
LP fair NAV            = $50.00
```

This is almost exactly the maximum $25 overcollateralization buffer:

```
initial excess collateral = 100 - 1.5*50 = $25
```

Therefore the ~$24.88 owner cash-out is **not new economic profit**. It is primarily release of the initial collateral cushion while preserving the 150% HF floor.

## Production waterfall

The safe production interpretation is:

1. Internal spread PnL is classified as transfer PnL, not distributable profit.
2. Restore LP fair NAV.
3. Pay real Base execution/gas.
4. Restore bridge HF to a safety target (recommended bootstrap target: 170-180%, hard floor 150%).
5. Only **external realized alpha** is distributable.
6. While total real capital is small, use 40% owner / 60% bridge.
7. Enable the full 40/30/20/10 split only after reserve and insurance are large enough.

External alpha can come from genuine cross-venue price differences, external LP fees, lending/staking yield, solver/MEV revenue, or other realized canonical cash flow. Artificial oracle divergence is not counted as external alpha.

## Run

```bash
cd valut_v7_100usd/model
python3 -m unittest -v test_v7.py
python3 optimize_v7.py
```
