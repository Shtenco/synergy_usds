# USDS in the SINERGY Financial OS federation

Status: additive architecture note. Existing Base-fork models, contracts, scripts and reports remain unchanged.

## Repository role

`Shtenco/usds` is the specialized research line for a USD-linked monetary/credit implementation family.

The wider Financial OS uses `SYNT` as the abstract transaction-money/unit-of-account interface. USDS may implement or experiment with a USD-denominated form of that interface, but its economic claims remain evidence-specific.

## Preserved core lesson

The existing Base-fork research correctly distinguishes:

```text
MINT USDS
 -> SELL into CPMM
 -> sale proceeds / productive principal
 -> price-restoration requirement
```

from actual external value creation.

Mint and sale proceeds do not create external dollar profit by themselves. Any `value_added` term must come from a separately evidenced productive or market process.

## Canonical accounting boundary

```text
minted USDS              -> liability / monetary supply effect
sale proceeds            -> asset relocation / financing flow
PP top-up                -> liquidity/restoration cost
external productive gain -> potential external revenue/value after evidence
```

The following are not sufficient to establish profit:

- newly minted USDS;
- a restored internal price;
- displayed pool TVL;
- synthetic model deposits;
- principal moved from pool to a productive bucket.

## Federation integration

- `synergy_financial_os` owns monetary constitution, accounting and issuance constraints;
- `ai_financial_system` preserves broader QE/QT/AMM/AI-CB research;
- `synergy_pay_system` executes and reconciles external settlement where integrated;
- `synergy_eurasian` can provide verified productive-demand/project evidence;
- `synergychain` may present USDS state but is not the accounting authority.

## Productive credit direction

A future canonical USDS credit path should follow:

```text
verified demand
 -> constitutional issuance/credit authorization
 -> eligible performing claim
 -> bounded release
 -> external production/revenue
 -> principal repayment
 -> QT / liability reduction
```

The authorization or mint itself is not HardNAV or revenue.

## Evidence status

Existing `value_added = multiple * sale` scenarios remain model assumptions unless backed by an independently demonstrated strategy/process. Fork execution can validate contract behavior and accounting invariants without validating the assumed external return multiple.

## Preservation rule

Do not delete the current Base experiments when adding canonical adapters. They are valuable because they document both positive scenario outputs and the negative result when external value added is absent.
