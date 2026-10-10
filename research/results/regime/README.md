# Regime experiment: no selection

Five predeclared designs were built and replayed on one continuous $100,000 account from January 2024 through September 2026. All failed the development gate. The original five-design experiment is closed without parameter retuning or access to its reserved historical validation.

| Design | Completed positions | Winners | Net USDT |
|---|---:|---:|---:|
| Unchanged Fibonacci baseline | 38 | 16 | +3,955.55 |
| Trend Fibonacci | 1 | 0 | -227.18 |
| Trend ATR | 0 | 0 | 0.00 |
| Range only | 6 | 0 | -1,226.27 |
| Combined Fibonacci | 7 | 0 | -1,450.37 |
| Combined ATR | 6 | 0 | -1,226.27 |

The new rules are too restrictive and mostly uneconomic at the stipulated costs. The trend Fibonacci branch rejected 53 of 55 rejection signals for insufficient net reward/risk; the ATR branch rejected 78 of 80. The range branch rejected 846 of 854. Its six actual fills all lost. A higher-level regime label did not establish an entry edge. More labels and filters do not fix the fee/reward problem.

Costs include 0.07% per side, two ticks of slippage, actual archived funding rates, BTC rounding, the shared exposure cap and 0.25% modeled account risk. No independent branch capital or overlapping positions is allowed. The net figures differ slightly from the prior sum of separately funded folds because this account does not reset at period boundaries.

Signals use completed hourly information, require two consecutive qualifying hourly classifications and decide on 15m closes. Five-minute execution is conservative; existing orders can fill before a cancellation decision. Tests cover future-prefix invariance, higher-timeframe publication, later entries, funding, quantity sizing, ambiguous endpoint consumption and one shared position.

All development data were previously inspected. [development.json](development.json) records source hashes, all qualifications, archive hashes, the three previously published cross-timeframe discrepancies, confidence intervals and stage counts. Daily continuous equity, funding and full trade logs accompany every design. No fresh or native TradingView profitability is claimed.

The subsequent [channel experiment](../channel/README.md) is a separate, one-design hypothesis declared after these failures. It changes the exit architecture instead of retuning these rejected candidates. Historical data were later opened only for that frozen channel design and its unchanged control; those periods are now inspected for future research.

Reproduce the known development results with `python research/competition/reproduce_strategy_studies.py regime --output /tmp/regime-audit`. This verifies frozen sources, data and exact output matches without selecting another candidate or making a fresh-validation claim. The original development-selection driver deliberately refuses to claim untouched historical validation when reserved archives already preexist. See the [data access ledger](../../DATA_ACCESS_LEDGER.md) for the current state.
