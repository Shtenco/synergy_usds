# LEGACY DISTILLATION V3 — usds

Assigned primitives:

- P051 STABLECOIN_PEG — REWRITE — 5 mechanisms / 197 occurrences.
- P052 STABLECOIN_PEG — PROMOTE — 1 mechanism / 12 occurrences.

Required gate: peg recovery must hold across multiple seeds after fees, gas, MEV and liquidity stress; oracle input must not be purely reflexive to the pool being controlled; reserve injections cannot be ex nihilo and every mint/burn must reconcile with reserve/liability treatment.
