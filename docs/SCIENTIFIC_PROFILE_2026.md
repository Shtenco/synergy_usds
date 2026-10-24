# USDS — scientific research profile: money issuance, CPMM and real value

## Research proposition

The repository asks a precise monetary-engineering question: **can a self-issued asset be sold in a constant-product pool, returned to its target price and generate externally distributable value without violating reserve accounting?** Its contribution is a reproducible simulator plus a Base-fork Solidity experiment that distinguishes minted balances, stablecoin reserves, external productive capital, gas and newly realised value added.

## Implemented model

In [base_v5_mint_sell_pp.py](../valut_v4/base_v5_mint_sell_pp.py), pool reserves x (USDS) and y (USDC) begin at equal target value. Issuing a fraction q of token reserve makes minted quantity e=qx. A fee-adjusted curve input changes the AMM pool before a separate real-USDC top-up restores target peg. The Solidity [Base experiment](../valut_v4/src/USDSMintSellPPBaseExperiment.sol) explicitly tracks minted token supply, stable balance, PP buffer, productive funds and cumulative externally realised additions.

For fee-adjusted input a and retained fee f, the ideal non-rounded constant-product sale output is:

$$
\Delta y=\frac{y\,a(1-f)}{x+a(1-f)}.
$$

The actual implementation separates swap fees and protocol fees, so this formula describes the underlying CPMM principle rather than replacing source-specific fee accounting. For target price 1 USDC/USDS, the real stablecoin restoration amount is

$$
T=\max(0,\ x_{\mathrm{after}}-y_{\mathrm{after}}).
$$

The operation consumes external liquidity. Sale proceeds moved from the AMM to productive capital are **transferred capital**, not independently created profit.

## Recorded scenario and scientific interpretation

The existing README documents a 100-cycle scenario starting with 1 USDC pool reserve and 1 USDC pre-funded PP buffer, and assuming separately generated value added equal to three times sale proceeds. Its modeled 0.3309 USDC distributable surplus per one initial external USDC is conditional on that **external productivity assumption**. The zero-external-value counterfactual produces operating costs rather than free income.

## Applications and reproducibility

The model is useful for investigating peg defense economics, liquidity requirements, monetary policy constraints and how minted instruments interact with externally paid settlement assets. Repeat the Python tests, reconcile all cash movements and Base-fork swaps, check USDC 6-decimal arithmetic and reserve conservation, then vary fees, productivity and liquidity stress.

**Research principle:** separate endogenous accounting units from externally realizable value. The project is a monetary mechanics laboratory, not a claim of unconstrained money creation.

[Simulator](../valut_v4/base_v5_mint_sell_pp.py) · [Solidity experiment](../valut_v4/src/USDSMintSellPPBaseExperiment.sol) · [Tests](../valut_v4/test_model.py)
