# Fibonacci settings comparison

Nine predeclared one-setting variations were evaluated: pivots 3/5/7, previous closed 4h EMA34/50/100, net reward floor 1.25/1.5/2.0, fresh-origin and displacement filters. Entries remain 15m, fixed 50%–61.8% first pullback, swing target. Risk remains 0.25%, notional cap 95%, maximum 1 BTC. Fees/reserve 0.07% per side, two tick slippage and actual funding in research.

## Recommendation

**Keep the current defaults: pivots 5, 4h EMA50, net R1.5, filters None. No better tuning passed the declared confirmation checks.** The separate `Fibonacci_Live_Impulse_Pullback_Pivot3_Research.pine` reproduces the selected three-bar candidate for paper comparison; it failed and is not a recommended upgrade. The original script is unchanged.

## 2024 comparison

Selection used only the two 2024 periods, with at least 15 trades, positive net, PF >=1.1, positive net excluding largest winner; ranking was net divided by sum of period 5m closing drawdowns. No parameter combinations or subsequent tuning. The choice and development hashes were committed before evaluating 2025 and 2026. All periods were already used in prior research, so this is chronological exploratory testing, not fresh validation.

| Setting | Trades | Net USDT | PF | Sum period drawdown | Eligible |
|---|---:|---:|---:|---:|---|
| baseline | 24 | 2,305.63 | 1.764 | 1,447.15 | True |
| pivot_3 | 19 | 2,963.21 | 2.524 | 1,021.45 | True |
| pivot_7 | 18 | 1,193.53 | 1.511 | 1,461.87 | True |
| trend_length_34 | 22 | 1,793.43 | 1.642 | 1,234.47 | True |
| trend_length_100 | 18 | 708.03 | 1.276 | 1,251.34 | False |
| minimum_net_r_1.25 | 32 | 2,408.11 | 1.599 | 2,041.09 | True |
| minimum_net_r_2.0 | 10 | 834.40 | 1.552 | 1,306.51 | False |
| breakout_filter_fresh_origin | 24 | 2,305.63 | 1.764 | 1,447.15 | True |
| breakout_filter_displacement | 14 | 1,540.84 | 1.883 | 880.98 | False |

## Frozen choice: pivots 3, remaining settings unchanged

| Settings | Year | Trades | Winners | Net USDT | PF | Net excluding best |
|---|---|---:|---:|---:|---:|---:|
| baseline | 2025 | 5 | 1 | -284.12 | 0.669 | -857.08 |
| baseline | 2026 | 9 | 5 | 1,911.38 | 3.227 | 1,174.84 |
| pivot_3 | 2025 | 8 | 1 | -913.80 | 0.385 | -1,486.75 |
| pivot_3 | 2026 | 8 | 3 | 449.99 | 1.421 | -133.97 |

Confirmation required >=10 trades, positive net, PF>=1.1 and positive net excluding the largest winner in **each year**. Pivot3 failed both years. Combined 2024–2026 net was $2,499.40 for pivot3 versus $3,932.89 for baseline, with 35/38 trades and 14/16 winners respectively. Do not present the better 2024 performance as a general improvement.

Higher-cost checks on 2025–2026: at 0.10% per-side fees, baseline/pivot3 net was $1,216.61/$122.36; at 20 ticks of slippage, $1,590.01/−$489.48. These reinforce retaining baseline, not profitability validation. Native Pine compilation remains unavailable. Binance prices are a proxy for Bitunix; 5m execution has intrabar path uncertainty and funding uses traded-price open as a mark-price proxy.

## Reproduction

`python research/competition/tuning_study.py development --output /tmp/fib-tuning`

Then freeze/review the generated selection before `python research/competition/tuning_study.py confirmation --output /tmp/fib-tuning`. Reports include all candidate development statistics, period-level confirmation, cost sensitivity, archive hashes and data discrepancies. Trade exports are `*_tuning_*_trades.csv`. Selection is deterministic; no later-period reselection.
