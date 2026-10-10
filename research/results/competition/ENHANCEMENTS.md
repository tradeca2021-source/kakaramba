# Follow-up strategy enhancements

Three predeclared exploratory comparisons use the same seven independent $100,000 account periods: 2024 H1/H2, 2025 H1/H2 and 2026 Q1/Q2/Q3. These periods have already been examined. Sum of period net is not a continuous portfolio return, and repeated experiments increase overfitting risk. Costs assume 0.07% per side and two tick slippage; verified Binance5m candles supply execution, and actual funding rates apply to carried positions with candle-open price as a mark-price proxy. Native TradingView compilation and Bitunix parity remain unverified.

## Entry execution

| Mode | Trades | Win rate | Net USDT | PF | Worst period 5m closing drawdown |
|---|---:|---:|---:|---:|---:|
| Rejection-break stop | 38 | 42.1% | 3,932.89 | 1.831 | 803.24 |
| Next-open market | 80 | 27.5% | 1,111.53 | 1.093 | 2,007.05 |
| Midpoint limit after rejection | 124 | 18.5% | -4,319.56 | 0.761 | 2,581.92 |
| Cost-bounded limit inside zone | 180 | 15.6% | -11,622.69 | 0.571 | 3,959.04 |

Cheaper entries make more signals eligible but produce many more stopped positions and fees. None meets the predeclared optional-mode criteria. Keep the stop entry. Orders are submitted only after rejection close; favorable limit gaps use limit price conservatively. In 2026 Q3, the control found25 rejections, skipped24 on the reward gate and canceled its one submitted order. Thus zero fills reflect trade eligibility and expiry rather than absence of structure signals.

## Close-confirmed stop protection

| Stop plan | Trades | Win rate | Net USDT | PF | Worst period 5m closing drawdown |
|---|---:|---:|---:|---:|---:|
| Fixed control | 38 | 42.1% | 3,932.89 | 1.831 | 803.24 |
| Cover costs after close reaches1.0R | 38 | 42.1% | 2,305.60 | 1.568 | 875.97 |
| Cover costs after close reaches1.5R | 38 | 42.1% | 2,881.00 | 1.610 | 882.55 |

Stops advance only after completed15m closes, using actual entry and submission-time risk, and become executable on later5m subbars. New stop prices include assumed entry/exit costs and adverse exit slippage, but exclude funding; they do not guarantee breakeven. Both plans reduced profit and increased worst period closing drawdown. Keep the fixed stop. Research trade exports preserve initial stop and separately identify exit stop and whether protection armed.

## Signal chart timeframe

| Chart | Trades | Winners | Net USDT | PF | Worst period 5m closing drawdown |
|---|---:|---:|---:|---:|---:|
| 15 minutes | 38 | 16 | 3,932.89 | 1.831 | 803.24 |
| 30 minutes | 18 | 3 | -1,769.13 | 0.439 | 1,083.75 |
| 60 minutes | 18 | 3 | -1,712.80 | 0.450 | 1,103.35 |

Canonical15m signal candles aggregate into complete UTC-aligned30m/60m candles. Execution still replays every5m subbar. Higher trend remains4h, and per-bar pivot, ATR, rejection and expiry settings remain the same; their elapsed durations increase on larger charts. This compares chart configurations rather than isolating timeframe from duration. Neither higher timeframe qualifies; keep15m. No candidate in any comparison met the qualification rules, so no qualifying-candidate cost sensitivity was run and no new trading mode was promoted.

## Shipped change

Pine v2 adds execution diagnostics, with entry/exit logic retained: freeze ATR and equity at submission; read actual entry and quantity for both open positions and trades closed between calculations; show actual-fill modeledR, stopped risk% and trigger slippage; label fills below the planned reward floor, above budget or beyond the planned bracket. Diagnostics exclude funding and are modeled estimates, not realized outcomes. They observe fills without reversing or altering them. No fresh profitability claim follows from this change.

## Reproduce

`python research/competition/live_entry_study.py --output /tmp/fib-entry-audit`

`python research/competition/protect_profit_study.py --output /tmp/fib-protection-audit`

`python research/competition/timeframe_study.py --output /tmp/fib-timeframe-audit`

Protocols are committed in `research/competition`; complete reports are `live_entry_audit.json`, `protect_profit_audit.json`, `timeframe_audit.json`. Per-period trade CSVs and counts expose concentration and failed periods instead of just aggregate profit. Tests exercise protection timing, cost-covering price arithmetic, complete signal aggregation, six-subbar30m replay and actual Pine fill-warning predicates. They do not compile Pine.
