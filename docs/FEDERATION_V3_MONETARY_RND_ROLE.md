# Federation V3 — USDS monetary R&D role

USDS maps to historical Part IX monetary experiments and remains a research asset, not the federation's accounting truth.

## Research questions
- stable-value mechanisms;
- reserve/redeemability models;
- mint/burn policy;
- external collateral vs endogenous backing;
- liquidity and run stress;
- redemption queues and settlement evidence.

## Required separation
- `unit_of_account`;
- `payment_asset`;
- `reserve_asset`;
- `risk/growth_asset`.

## Invariants
- minted supply is not external wealth;
- peg mark is not reserve value;
- reserve claims require verifiable external assets/liabilities;
- settlement belongs to `synergy_pay_system`;
- accounting interpretation belongs to `synergy_financial_os`.
