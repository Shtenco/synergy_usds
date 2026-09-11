# LEGACY DISTILLATION V2 — Import Queue

Canonical owner: `Shtenco/usds`

Nothing in this queue is auto-promoted to production. Every mechanism must pass the listed gate in this repository authority boundary.

| Priority | ID | Family | Action | Occurrences | Test gate | Representative |
|---|---|---|---|---:|---|---|
| P0_REWRITE | M162 | STABLECOIN_PEG | REWRITE_REQUIRED | 139 | `multi_seed_peg_stress` | syncFromChain |
| P1_REWRITE | M164 | STABLECOIN_PEG | REWRITE_REQUIRED | 17 | `multi_seed_peg_stress` | SYNC |
| P1_PROMOTE_WITH_GATE | M163 | STABLECOIN_PEG | PROMOTION_CANDIDATE | 25 | `multi_seed_peg_stress` | _grantAllRoles |
| P1_PROMOTE_WITH_GATE | M165 | STABLECOIN_PEG | PROMOTION_CANDIDATE | 12 | `multi_seed_peg_stress` | _update |
| P1_PROMOTE_WITH_GATE | M166 | STABLECOIN_PEG | PROMOTION_CANDIDATE | 12 | `multi_seed_peg_stress` | recalc |
| P1_PROMOTE_WITH_GATE | M167 | STABLECOIN_PEG | PROMOTION_CANDIDATE | 4 | `multi_seed_peg_stress` | pegMint |
