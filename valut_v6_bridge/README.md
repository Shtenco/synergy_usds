# Perpetual Arbitrage Engine V6

V6 проверяет исходное ТЗ через полный баланс canonical assets и redeemable synthetic liabilities.

## Ключевой вывод

Управляемый внутренний ценовой градиент не создаёт новую canonical стоимость. Положительный PnL отдельного арбитражного бота в цикле

USDC -> WETH outside -> mint ETHS -> sell ETHS inside -> USDS -> redeem USDC

почти один-в-один равен потере fair NAV внутреннего LP, за вычетом внешних комиссий, price impact и газа.

Поэтому основной инвариант V6:

```
Protocol Equity = Canonical Assets - Redeemable Synthetic Liabilities
```

и выплаты владельцу разрешаются только из нового реализованного canonical revenue после восстановления target Health Factor.

## Исправление направления арбитража

Cycle A прибылен, когда внутренняя цена ETHS выше внешней цены WETH:

```
P_internal > P_external + fees + slippage + gas
```

Если ETHS внутри дешевле внешнего ETH, выгодное направление обратное:

```
USDS -> buy ETHS inside -> burn/unlock WETH -> sell WETH outside -> USDC
```

То есть в исходном ТЗ направления были подписаны наоборот.

## Математика

Для внешнего CPMM с резервами Xe WETH, Ye USDC и fee fe покупка ровно q WETH стоит:

```
Cext = [Xe*Ye/(Xe-q) - Ye] / (1-fe)
```

Для внутреннего CPMM Xi ETHS, Yi USDS и fee fi продажа q ETHS выдаёт:

```
S = Yi - Xi*Yi/(Xi + q*(1-fi))
```

PnL бота:

```
BotPnL = S - Cext - gas
```

Изменение fair NAV внутреннего LP по внешней цене:

```
DeltaLP = q*Pext - S
```

И выполняется закон сохранения:

```
BotPnL + DeltaLP ~= -(external execution cost + gas)
```

Lock/Mint и Burn/Unlock 1:1 не меняют bridge equity: актив и redeemable liability изменяются одинаково.

## Цена восстановления искусственного спреда

После продажи q ETHS внутренние резервы становятся Xi' и Yi'. Чтобы вернуть старую целевую цену P* односторонним mint USDS:

```
Mreset = P* * Xi' - Yi'
```

Для малой сделки Mreset примерно равно 2*S. Поэтому perpetual reset искусственного градиента быстро наращивает redeemable liabilities.

## Численный стресс-тест

Параметры:

- Pext = $2,500
- Pint = $30,000
- internal pool = 100 ETHS + 3,000,000 USDS
- trade = 1 ETH
- external TVL = $118M CPMM approximation
- external fee = 5 bp
- internal fee = 30 bp
- gas = $0.05
- bridge assets = $6M
- bridge liabilities = $3M
- start HF = 200%
- minimum HF = 150%

Первый цикл:

```
external spend        = $2,501.3566
USDS received         = $29,614.7410
bot PnL               = $27,113.3344
internal LP fair loss = $27,114.7410
reset mint            = $59,614.7410 USDS
```

Без распределения bot PnL система падает ниже HF 150% на цикле 20.

С исходным распределением 40/30/20/10, причём 30% оптимистично сразу возвращаются в canonical bridge reserve, 20% остаются canonical insurance, а 10% уменьшают liability через burn, система падает ниже HF 150% на цикле 24.

Следовательно, распределение замедляет исчерпание запаса, но не делает engine perpetual.

Если не восстанавливать искусственную цену административным mint, обычный арбитраж сам уничтожает спред и постепенно сходится к внешней цене.

## Контракты V6

`BridgeVaultV6`

- Base native USDC + WETH как canonical assets
- USDS + ETHS как redeemable liabilities
- 1:1 deposit/mint и burn/redeem
- mark-to-market bridge NAV
- Health Factor по всем redeemable liabilities
- compensation/reset mint запрещён, если после mint HF ниже порога
- `requiredUSDCForAdditionalUSDSMintRaw()` показывает, сколько нового реального USDC нужно перед дополнительной эмиссией

`InternalCPMMV6`

- ETHS/USDS constant-product AMM
- swap fee
- fair NAV LP по внешней ETH/USD цене

`AerodromeCycleExecutorV6`

На Base fork выполняет реальную внешнюю часть:

```
native USDC -> Aerodrome -> WETH
WETH -> BridgeVault -> ETHS
ETHS -> InternalCPMM -> USDS
USDS -> BridgeVault -> native USDC
```

`ProfitDistributorV6`

- принимает только реально поступивший native USDC
- сначала закрывает deficit до target HF
- затем применяет 40/30/20/10
- internal mint не считается revenue

## Base addresses

```
Chain ID          8453
USDC              0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
WETH              0x4200000000000000000000000000000000000006
Aerodrome Router  0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
Aerodrome Factory 0x420DD381b31aEf6683db6B902084cB0FFECe40Da
```

## Запуск

Математика:

```bash
cd valut_v6_bridge/model
python3 -m unittest -v test_perpetual_bridge_v6.py
python3 perpetual_bridge_v6.py
```

Base mainnet fork:

```bash
cd valut_v6_bridge
BASE_RPC_URL=https://mainnet.base.org forge test --match-contract BaseForkBridgeV6Test -vvv
```

Для стабильного CI лучше использовать archive/full Base RPC.

Рабочая экономическая интерпретация проекта: inventory-backed market maker + bridge + real-yield/fee engine + solvency-controlled rebalancer. Источником роста canonical equity должны быть реальные внешние fees, genuine cross-market mispricing, lending/staking yield, solver/MEV revenue или другой фактически реализованный внешний денежный поток.
