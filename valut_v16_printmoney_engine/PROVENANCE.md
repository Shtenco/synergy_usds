# V16 source distillation

V16 is an original implementation. It does not copy source code from the projects below; it distills their economic/control patterns.

## TejasS1233/aribitrage_trading_system
Useful pattern: MoneyPrinter execution + profit validation. The source encyclopedia describes `printMoney()` as self-funded arbitrage and `flashPrintMoney()` as flash-loan arbitrage, alongside profit-or-revert execution.

## Inverse Finance Fed
Source: `code-423n4/2022-10-inverse/src/Fed.sol`.
Useful pattern: explicit expansion/contraction, supply ceiling, market authorization, and separation of supplied principal from market profit.

V16 adaptation: expansion/contraction is applied to q-assets by default. External senior liabilities may expand only through a backed release.

## Beanstalk Sun / Well Minting Oracle
Sources:
- `BeanstalkFarms/Beanstalk/.../Sun.sol`
- `BeanstalkFarms/Beanstalk/.../LibWellMinting.sol`

Useful pattern: measure a pool imbalance (`deltaB`) from time-weighted/instantaneous reserves, then perform state-dependent monetary policy.

V16 adaptation: `sunrise(delta_quote)` changes virtual QE inventory and the internal throughput buffer, not canonical NAV.

## SORA XST
Source: `sora-xor/sora-docs/src/xst.md`.
Useful pattern: primary market maker mints/demints synthetic liquidity during order execution; a synthetic claim is explicitly not a claim on actual USD.

V16 adaptation: qUSDS/qETHS provide effectively elastic internal liquidity but are non-redeemable.

## Sky/Maker dss-lite-psm
Source: `sky-ecosystem/dss-lite-psm/src/DssLitePsm.sol`.
Useful pattern: pre-minted liquidity buffer plus permissionless `fill`, `trim`, `chug` style off-band inventory management.

V16 adaptation: protocol-internal escrowed senior inventory is excluded from external liabilities until released against canonical inflow and the HF check succeeds.

## Behodler/Limbo
Sources:
- `Behodler/limbo/documentation/MonetaryPolicy.md`
- `Behodler/limbo/contracts/Limbo.sol`

Useful pattern: protocol-created supply is paired with protocol-owned liquidity and used to tilt/flatten an external AMM curve, with explicit warnings that excessive issuance leads to dilution/hyperinflation.

V16 adaptation: QE can deepen or tilt the internal fork pool, but cannot be booked as consolidated profit.

## V16 consolidated invariant

```
Canonical NAV = canonical assets owned by the protocol
External L    = redeemable senior claims outside protocol control

HF = Canonical NAV / External L
```

Excluded from canonical NAV:

- qUSDS/qETHS;
- protocol-internal swap fees;
- internal arbitrage PnL;
- escrowed senior buffer still controlled by the protocol.

This gives the system a "printing press" for internal liquidity without allowing the accounting engine to confuse printing with economic profit.
