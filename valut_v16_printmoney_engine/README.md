# V16 PRINTMONEY ENGINE

V16 combines the useful monetary-policy patterns found in open-source DeFi while preserving the strict owner-only consolidated accounting introduced in V14/V15.

## Architecture

```
                         FOREIGN CAPITAL
                 Deep Base WETH/USDC venues
                           ^       |
                           |       v
                    Arb / Settlement Gate
                           ^       |
                           |       v
                  Bridge / Netting Buffer
                    ^             |
                    |             v
              Fork Senior ETHS/USDS
                    ^             |
                    |             v
          QE qETHS/qUSDS virtual PMM
                    ^
                    |
             Sunrise / Fed Policy
```

All components below the foreign pool are protocol-owned.

## Three kinds of "money"

### 1. qUSDS / qETHS — QE money

- algorithmically mintable/burnable;
- can be very large;
- provides virtual/internal liquidity;
- can recharge the gradient;
- cannot redeem for USDC/WETH;
- never counts toward canonical NAV.

### 2. Escrowed senior inventory

A Maker/Sky-inspired pre-positioned buffer.

It can be created inside protocol-controlled contracts for fast execution, but is locked inside the protocol boundary.

While escrowed:

```
external liability change = 0
canonical NAV change      = 0
```

It becomes a real senior liability only when released outside protocol control.

### 3. Circulating senior USDS/ETHS

- leaves protocol control;
- is redeemable;
- therefore counts as external liability;
- can only be released if the post-release HF remains above target.

## $100 bootstrap

```
canonical assets             = $100
external senior liabilities  = $50
HF                           = 200%
target HF                    = 180%
hard HF                      = 150%
```

Maximum 1:1 senior release against equal canonical inflow while preserving 180% target HF:

```
x <= (A - hL)/(h - 1)
x <= (100 - 1.8*50)/0.8
x <= $12.50
```

The internal QE and escrow buffers may be much larger than $12.50 because they are not external redeemable claims.

## Sunrise

Borrowing the Beanstalk control idea, every policy epoch measures fork/bridge imbalance.

```
deltaQuote > 0 -> expand qUSDS
deltaQuote < 0 -> contract qUSDS
```

At the same time the engine fills/trims the internal execution buffer to match expected throughput.

Neither operation creates canonical profit.

## MoneyPrinter gate

The arbitrage executor can book profit only when:

```
real external gross gain
- external DEX fees
- price impact
- gas
- MEV/adverse selection
>= minimum profit
```

Otherwise the trade reverts / is not sent.

This follows the useful part of the open-source MoneyPrinter pattern while preventing an internal fork premium from being misclassified as system profit.

## Why this is stronger than V9-V15

The system can now maintain a very large internal "monetary base" without forcing the canonical balance sheet to match it dollar-for-dollar.

But the accounting remains strict:

```
QE liquidity != wealth
escrow inventory != external debt
external circulating senior == debt
realized external canonical gain == profit
```

This is the cleanest implementation so far of the original printing-press idea.

## Next experiment

V17 should connect this policy core to the live Base-fork router:

1. use real Base WETH/USDC pool state;
2. run `Sunrise` every block;
3. recharge q-liquidity;
4. pre-fill/trim bridge inventory;
5. route only residual external settlement;
6. execute only profit-or-revert external trades;
7. report consolidated canonical NAV and external liabilities separately.
