# Base fork: MINT → SELL → 100% purchasing power

Target experiment: mint USDS, sell into USDS/USDC CPMM, retain the received USDC as productive capital, and finish the transaction with pool price exactly $1 using a pre-funded PP buffer. The PP buffer is later replenished from realized external value-added.

Полная экономическая интерпретация системы со стартовым капиталом ровно `$2`
и ограничения допущения `3x` приведены в
корневом [`README.md`](../README.md).

Base native USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.

## Запуск

Запускайте команды из каталога `valut_v4`. Нужны Foundry, архивный/full RPC
Base и адрес держателя с балансом не менее 10 native USDC на выбранном блоке:

```bash
BASE_RPC_URL=<archive/full Base RPC> \
BASE_USDC_WHALE=<holder with >= 10 USDC at fork head> \
forge test --match-contract BaseForkMintSellPPTest -vvv
```

Проверка непрерывной математической модели не требует RPC:

```bash
python3 -m unittest -v test_model.py
```

Fork-набор проверяет одиночный и десять последовательных циклов, восстановление
цены, сохранение выручки в productive principal и равенство фактического баланса
USDC сумме всех учетных корзин контракта.

Important Base fee accounting: total fee is L2 execution fee + L1 data/security fee. `tx.gasprice * gasUsed` measures only the L2 execution component in the fork harness. For a production benchmark, query Base `GasPriceOracle` at `0x420000000000000000000000000000000000000F` using `getL1Fee(serializedTx)` or `getL1FeeUpperBound(txSize)` and add it to execution gas.

The x3 value-added deposit in the fork test is deliberately synthetic: fork USDC is transferred from an impersonated holder only to validate accounting and invariant mechanics. It does **not** prove an economic strategy can produce x3. That proof belongs to the productive engine backtest.
