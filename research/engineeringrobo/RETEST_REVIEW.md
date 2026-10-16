# Breakout and retest follow-up

**Neither retest variant qualified.** The structural version improved September but lost in both earlier periods. September has only six executed structural trades; selecting it from that outcome would be post-hoc selection. No Pine default or live order logic was changed.

This experiment follows the failed entry-filter study. Its bounded rules were written to `retest_protocol.json` before this run. It reuses previously inspected December2025–September2026 Binance BTCUSDT perpetual archives; no fresh or Bitunix validation is claimed.

## Fixed rules

A main Supertrend flip arms a frozen prior24h high for longs or low for shorts. The boundary excludes the signal candle. Require a closed-bar break within8bars, followed by a retest within8more bars. A retest must touch the boundary zone, close back on the breakout side, and have a candle body in the trade direction. The breakout candle cannot confirm its own retest. An opposite main signal cancels the setup; a close beyond the boundary in the wrong direction by more than0.25signalATR invalidates it.

Entry is the next15m open after confirmation, with adverse slippage. One variant preserves the original1.5ATR stop/2ATR target, with ATR frozen from the original signal. The structural variant freezes the stop beyond the retest candle by0.25signalATR and targets twice actual entry-to-stop distance. It rejects gap-invalidated stops and targets smaller than3times modeled round-trip friction. Opposite original main signals close any open trade on the following open even when no new retest entry exists.

All primary accounts start with $100,000 and trade0.1BTC to avoid the buying-power confounding seen at1BTC. Base commission0.07% per side, tick0.1, slippage2ticks, supplied historical funding with last-price mark proxy, conservative5mstop-first replay. Each period is an independent account, and pre-period setups cannot enter it.

| Period | Original control | Retest, same ATR exits | Retest, structural stop / 2R | Structural trades | Structural mean net |
|---|---:|---:|---:|---:|---:|
| development | $-7,266.46 | $-739.91 | $-415.24 | 34 | $-12.21 |
| comparison | $-2,191.32 | $-193.89 | $-233.39 | 8 | $-29.17 |
| historical_review | $-416.11 | $113.80 | $268.92 | 6 | $44.82 |

The development structural result was34trades, PF0.656 and net−$415.24; July–August8trades, PF0.071 and−$233.39; September6trades, PF3.608 and+$268.92. Across independent periods the structural variant totals48trades and−$379.72, not a continuous compounding backtest. The retest with unchanged ATR exits also remained negative overall.

## Interpretation

- Waiting reduced exposure dramatically:535original development signals became44confirmed retests and34structural entries after cost checks. Much of the smaller total loss comes from taking far fewer trades.
- The same-exit retest variant had a worse development mean trade (−$16.82 versus control−$13.58), and July–August also worsened (−$17.63 versus−$11.24). Timing alone did not establish a better entry.
- Structural stops plus the cost gate improved the development mean to−$12.21, but July–August deteriorated to−$29.17. September improved to+$44.82 on just6trades. That instability prevents promotion.
- September stayed positive under both declared cost stresses, but did not rescue the failed development or July–August results. Higher fees change economic eligibility, so stress trade counts differ.

## Decision and next evidence

Do not present this as a profitable refinement. Retain it as a reproducible research candidate. Native TradingView signal/fill matching and actual Bitunix fee/data verification remain unresolved. A next experiment should reserve forward data before any further adjustment; repeatedly changing thresholds on these same losing periods cannot create independent validation. If studying a different breakout level, session, signal source or exit design, define it as a new hypothesis rather than silently retuning this one.

## Verification

227unit tests pass, including long/short symmetry, no same-bar retest, original-opposite cancellation, invalidation, inclusive retest deadline, expiry, no cross-period setups, prefix causality, gap-invalidated structural stops, actual-fill 2R math and original-opposite exits without a new retest. Synthetic tests verify mechanics only.

The `retest_results` directory retains the36period/cost/size trade ledgers, setup records and JSON summaries, with protocol/source/archive hashes. Local full run: `/workspace/engineeringrobo-retest-results/20261015T143532324840Z`. Reproduce: `python3 -B research/engineeringrobo/retest_study.py`. Python is not native Pine parity; funding mark approximation, stop-first5m ties, sampled drawdown and conservative full margin closure remain limitations.
