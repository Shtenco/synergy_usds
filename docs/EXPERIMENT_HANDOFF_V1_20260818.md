# USDS Experiment Handoff V1 — 2026-08-18

## Purpose

This additive layer standardizes how USDS monetary experiments report their results to the wider SINERGY federation without claiming accounting authority.

The historical Base-fork models, contracts, deployment scripts, reports and README remain unchanged.

## Core accounting boundary

`minted_usds_notional` and `sale_proceeds` are reported for experiment observability but are deliberately excluded from `external_pnl_candidate`.

The research candidate is:

```text
external_pnl_candidate
  = independently evidenced external_value_added
  - restoration_external_cost
  - gas_and_external_costs
```

This value is still **not** recognized Financial OS profit. The handoff always carries:

```text
accounting_authority = Shtenco/synergy_financial_os
financial_os_recognition = NOT_PERFORMED
classification = RND_ONLY
```

A positive `external_value_added` requires an independent 64-hex evidence digest. Fork and live-observed execution also require separate execution evidence.

## Closure gates

A result cannot become `HANDOFF_REVIEWABLE` if:

- price restoration is incomplete;
- USDS liability remains open;
- supply closure is incomplete;
- required evidence is missing.

The only handoff verdicts are `RND_BLOCKED` and `HANDOFF_REVIEWABLE`.

`HANDOFF_REVIEWABLE` is not a journal entry, profit recognition, authorization to mint, or permission to trade.

## Numeric discipline

All economic values are finite `Decimal` values and serialize to unique plain decimal strings. `NaN`, positive/negative infinity and negative amounts are rejected. Fork block numbers are bounded to the cross-language safe integer range.

## Credential boundary

The handoff accepts no credentials, private keys or signing authority. `credential_inputs_allowed` is permanently false.

A historical key-named file exists in repository history/root. This new layer does not read, copy or consume its contents. Any key material that has ever been tracked in Git must be treated as compromised for future live use and replaced outside the repository with a fresh secret managed through an appropriate secret/HSM/MPC boundary.

The old tracked artifact is preserved solely because this project uses non-destructive provenance. Preservation must never be interpreted as permission to reuse it.
