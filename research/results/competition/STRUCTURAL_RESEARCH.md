# Structural redesign research

Seventeen alternatives across six design families were tested on the same seven previously inspected independent-account periods. None qualified for replacing or extending the current trading rules. These are exploratory results, not unused validation; repeated comparisons increase overfit risk.

The baseline remains38 trades,16 winners, summed period net+$3,932.89, PF1.831 and worst period5m closing drawdown$803.24. Several periods still lose. Sum of account-fold net is not a continuous portfolio return. Costs,actual funding,exposure caps and0.25%risk remain included. Native TradingView and venue-exact Bitunix parity are unverified.

| Family / alternative | Trades | Net USDT | PF | Positive periods | Worst period drawdown | Net excluding best |
|---|---:|---:|---:|---:|---:|---:|
| exhaustion / extended | 12 | 1,260.04 | 1.869 | 2/7 | 573.09 | 406.30 |
| exhaustion / rapid | 35 | 2,780.34 | 1.618 | 4/7 | 1,043.74 | 2,001.39 |
| exhaustion / both | 10 | -91.59 | 0.937 | 2/7 | 502.50 | -602.97 |
| micro_momentum / price_slope | 4 | 844.56 | 2.987 | 1/7 | 573.09 | -9.18 |
| micro_momentum / alignment | 2 | 645.46 | 4.099 | 1/7 | 573.09 | -208.28 |
| micro_momentum / both | 2 | 645.46 | 4.099 | 1/7 | 573.09 | -208.28 |
| failed_break / reversal_618 | 0 | 0.00 | n/a | 0/7 | 0.00 | 0.00 |
| failed_break / reversal_786 | 0 | 0.00 | n/a | 0/7 | 0.00 | 0.00 |
| failed_break / reversal_origin | 16 | -1,434.55 | 0.485 | 1/7 | 1,041.89 | -1,929.77 |
| failed_retest / reversal_618 | 1 | -211.14 | 0.000 | 0/7 | 281.55 | 0.00 |
| failed_retest / reversal_786 | 3 | 16.15 | 1.039 | 1/7 | 281.55 | -417.71 |
| failed_retest / reversal_origin | 12 | -326.05 | 0.830 | 2/7 | 670.06 | -996.22 |
| macro_setup / macro2 | 34 | 1,039.01 | 1.197 | 4/7 | 1,189.82 | 89.57 |
| macro_setup / macro3 | 25 | 451.08 | 1.115 | 3/7 | 1,269.52 | -498.36 |
| macro_setup / macro5 | 21 | -814.11 | 0.782 | 3/7 | 1,259.41 | -1,755.80 |
| dual_clock / micro_first | 42 | 2,921.96 | 1.504 | 4/7 | 1,383.33 | 1,970.58 |
| dual_clock / macro_first | 43 | 2,699.58 | 1.449 | 4/7 | 1,383.33 | 1,750.14 |

## What changed in the research

- Exhaustion guards reject over8ATR impulses or large fast rebounds. They removed winners along with losers.
- Completed5m momentum agreement at the15m rejection close almost eliminates entries, because a first pullback naturally runs against local momentum. The higher profit factors depend on one large winner and tiny sample sizes.
- Failed-break reversals require midpoint and broken-level reclaim plus opposite5m momentum. The61.8%/78.6% direct targets cannot pass the net reward gate; full-origin recovery loses money.
- Failed-break retests arm after reclaim and wait for later support/resistance rejection. Target visits on the confirmation candle are explicitly consumed instead of creating a stale opportunity. Samples remain small and uncompetitive.
- Four-hour pivots supply structure and targets while15m candles supply rejection entries and stops. Only closed4h information is delivered, with breakout detection before updating newly confirmed pivots. Macro2 profits in2025H2 and takes2026Q3 trades, but total profit is lower.
- Dual-clock arbitration uses one account, one active setup, one pending order and one position. It picks one source while idle; busy signals are discarded rather than queued or backdated. Both source priorities reduce net and increase drawdown versus the baseline. This combination was proposed after seeing standalone macro outcomes and is explicitly post-hoc.

All primary candidates failed their declared qualification conditions. Conditional higher-cost sensitivity was therefore not run. No threshold retuning or default promotion followed from these outcomes.

## Code and checks

The stable `research/competition/engine.py` remains unchanged. New designs live separately in `experimental_engine.py`; experimental output records its SHA256. Six protocols were committed before their respective experiment runs; each report publishes protocol hashes, archive hashes, data quality, per-period summaries, counts, candidate qualifications and all trade CSVs. The final source was rerun for all six reports.

Tests verify exact stable-control parity, EMA prefix causality, final-closed5m data timing, reversal direction for both sides, retest entries on later bars, target-visited consumption, allowed macro transition after reclaim, closed4h break publication, prior-pivot use, macro setups without15m pivots, single-account arbitration, discard of busy signals and complete4h aggregation. Native Pine compilation is not available.

Reproduce each using `python research/competition/<family>_study.py --output /tmp/<family>-audit`, where family is one of the six table prefixes.

## Active and rejected Pine files

The active script is [Fibonacci_Live_Impulse_Pullback.pine](../../../Fibonacci_Live_Impulse_Pullback.pine), with profile **Baseline BTC15m (experimental)**. A chart titled **REJECTED Fib Pivot3** is a different, rejected research artifact; changing its inputs does not turn it into the active baseline. The rejected file is now archived in `research/rejected/` to reduce accidental selection. None of the new rejected Python prototypes is shipped as a Pine upgrade.
