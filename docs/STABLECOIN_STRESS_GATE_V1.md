# Stablecoin Stress Gate V1

Distilled from the legacy SYNERGY currency/peg simulations audited on 2026-09-11.

A stablecoin model is **not accepted from final price deviation alone**. A path that returns near peg after a deep transient failure can still be economically unsafe.

Mandatory metrics:

- maximum positive/negative peg excursion;
- time outside ±0.5%, ±1%, ±2%, ±5% bands;
- reserve depletion and minimum reserve ratio;
- redemption capacity under concurrent exits;
- oracle/reference-price divergence;
- external liquidity depth and executable slippage;
- intervention count, size and cost;
- gas, MEV and congestion stress;
- liability coverage and insolvency probability;
- recovery half-life after a shock;
- dependence on mint/burn or internal LP marks;
- left-tail Monte Carlo outcomes, including P5.

The legacy stress run showed that large transient deviations can occur even when a saved long-horizon result ends much closer to target. Therefore `final_price ≈ target` is never sufficient production evidence.

Promotion rule: stablecoin mechanics stay `R&D` until redemption, external-liquidity, oracle, liability and left-tail stress gates pass under independently reproducible scenarios.
