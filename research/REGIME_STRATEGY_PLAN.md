# Next strategy experiment: regimes first, Fibonacci as a test

Status: a research plan, not an implemented or profitable strategy. The existing Pine baseline stays unchanged. Freeze this plan and the machine-readable protocol before replaying new candidates; do not silently retune failed candidates.

Execution update: all five designs were implemented and failed the frozen development gates. That experiment stopped without retuning; see [results](results/regime/README.md). A separately predeclared, single channel design then qualified in development and failed its source-frozen historical test; see [channel results](results/channel/README.md). No new Pine design was promoted. The [data ledger](DATA_ACCESS_LEDGER.md) records that the older history is now inspected.

## What we need to improve

The current baseline has 38 completed positions and 16 winners across seven previously inspected, separately funded periods. Several periods lose and one has no fills. Its summed period profit is not a continuous portfolio return. Seventeen recent structural alternatives failed to beat it under their declared criteria.

The next experiment changes the entry hypothesis. It tests whether different market conditions need different trades, and whether Fibonacci improves those trades after execution costs. More filled orders and a higher win rate are secondary objectives; positive net expectancy and controlled drawdown come first.

## Fixed trading design

- Venue for the eventual chart check: Bitunix BTCUSDT perpetual, standard candles. Research venue: Binance USD-M BTCUSDT; report the venue difference explicitly.
- Execution chart: 15 minutes. Regime decisions: completed one-hour candles only. Do not optimize the chart timeframe in this experiment.
- One account, one position, no pyramiding or simultaneous branch portfolios. Both branches share the same risk and exposure limits.
- Risk per position: 0.25% of equity including modeled execution costs. Preserve BTC quantity rounding, 95% notional cap and maximum 1 BTC. No leverage increase to improve reported profit.
- Base execution model: 0.07% per side including the existing reserve, two ticks of slippage, actual research funding, and five-minute intrabars. Use conservative stop-first handling when event order cannot be resolved.
- No decision may use an unfinished higher-timeframe candle, future pivot, or entry before the signal candle closes. Funding and fees apply to the actual position held.

## Regime classification

Use one simple, interpretable classifier rather than stacking many filters. On completed hourly candles, calculate ATR(14), EMA(50), and a 20-bar efficiency ratio: absolute 20-bar price change divided by the sum of absolute one-bar changes. Treat a zero denominator as zero efficiency.

- Trend: efficiency at least 0.35, price on the corresponding side of EMA(50), and EMA changing in that direction over the last five completed hours by at least 0.20 hourly ATR.
- Range: efficiency at most 0.20 and absolute five-hour EMA change at most 0.20 hourly ATR.
- Transition: everything else; do not arm new trades.

Require the same classification on two successive completed hourly candles before enabling new setups. Once an entry order exists, cancel it on loss of its qualifying regime. A regime change never removes a live protective stop. These initial thresholds are design choices, not demonstrated optimal settings; do not search a threshold grid.

## Entries and exits

### Trend continuation

A directional 15-minute close must break the high or low of the previous 20 completed 15-minute candles, agree with the hourly trend, and have a body at least 0.5 ATR(14). Anchor the impulse to the opposite edge of that preceding range. Track the closed-bar endpoint until the first pullback; freeze it when the pullback first visits the entry band. If a candle both extends the impulse and touches a band based on its previous endpoint, discard the ambiguous setup.

Compare two entry bands, keeping every other rule identical:

1. Fibonacci: a 50%–61.8% retracement of the frozen impulse.
2. Non-Fibonacci: a 1.0–1.5 ATR pullback from the frozen endpoint, using ATR fixed at the breakout close.

Both require a directional rejection candle to close back beyond the nearer band edge, on the first touch or the next candle. Enter with a stop order one tick beyond the rejection candle. The protective stop is beyond the entire rejection sequence by 0.20 current ATR. Target is a fixed 2R gross distance from the trigger, with the same minimum 1.5 net reward/risk gate after modeled costs. No partial exit or trailing stop in this first comparison.

An unused setup expires after 16 bars; a submitted order expires after three later bars. Cancel on a new pullback extreme, broken impulse origin, already visited target, lost trend classification, or expired setup. Record why each rejected order failed instead of lowering the payoff gate to manufacture more trades.

### Range failed breakout

Freeze the prior 20 completed 15-minute candles' high, low and midpoint. A candle must sweep an edge by at least one tick, close back inside, have a body in the reversal direction and close in the inner half of its own candle range. Trade toward the frozen range midpoint using a stop entry beyond that rejection candle and a protective stop beyond its sweep by 0.20 ATR(14).

Keep the same 1.5 net reward/risk gate and three-bar order lifetime. Cancel if the sweep extends, the midpoint target is visited, the hourly range classification ends, or the lifetime expires. A candle that already visited the midpoint before confirming its rejection cannot arm a trade. No trend branch trades are allowed while the range branch has an order or position.

## Finite comparison budget

Run exactly these five new designs plus the unchanged baseline:

| Candidate | Trend entries | Range entries |
|---|---|---|
| Trend Fibonacci | Fibonacci rejection | Disabled |
| Trend ATR | ATR rejection | Disabled |
| Range only | Disabled | Failed breakout |
| Combined Fibonacci | Fibonacci rejection | Failed breakout |
| Combined ATR | ATR rejection | Failed breakout |

No extra target, threshold, timeframe or risk grids. Branch diagnostics must distinguish lack of setups, rejected payoff, canceled orders and losing fills. Compare the two combined strategies to test Fibonacci's contribution; compare each combined strategy to its constituent branches to expose interference in the shared account.

## Data and selection sequence

1. Write the executable protocol and verify the causal replay engine against hand-worked entries, exits, funding events, hourly publication times and prefix invariance. Retain the stable engine and baseline control.
2. Use already inspected 2024–2026 data for development and ranking only, with earlier candles as warm-up. Publish continuous-account equity and half-year summaries, not just summed reset-account profits. Apply the same execution and cost assumptions to all candidates and the baseline.
3. Select at most one candidate before opening additional validation data. It must exceed baseline net profit on the common development period, have at least 100 completed positions, at least four positive half-year blocks, positive net excluding its best trade, and maximum marked-to-market drawdown no greater than 5%. Rank qualifying candidates by worst half-year net, then total net; do not rank only by win rate.
4. Freeze the selected candidate's code, parameters and checksums. BTC 2021–2022 archives were not found in the current workspace inventory. Reserve 2020 as warm-up and 2021–2022 as a possible unopened historical stress test, subject to archive/funding availability and an audit that these periods were not previously inspected. Do not download or inspect those test outcomes before selection. Earlier years test generalization to older regimes; they are not forward validation.
5. For that historical test, require positive aggregate net, at least three positive half-year blocks, at least 50 completed positions, net profit factor at least 1.20, positive net excluding the best trade and drawdown at most 5%. Repeat the frozen candidate and baseline under 0.10% per-side fees and, separately, 20-tick slippage; the candidate must remain net positive in both. Publish failures as well as successes. Any subsequent changes invalidate this test as unopened validation.
6. If no candidate qualifies, stop this experiment and report the failure. If reserved archives or funding are unavailable, report validation incomplete; do not substitute already inspected data and call it fresh. Passing the older stress test still leaves genuinely future evaluation outstanding.

The 100/50-trade thresholds are minimum screening requirements, not proof of profitability. Report uncertainty using contiguous-week block resampling of daily account returns, with a fixed seed, and do not treat individual trades as independent evidence. Multiple comparisons and historical venue differences remain limitations.

## Pine and deployment gates

Only a qualified frozen design proceeds to a new, clearly named Pine script. Keep the current experimental baseline available. Show actual effective inputs, regime, branch, order state, rejection reason and actual-fill reward/risk. Use the existing profile protection against stale saved inputs.

Native compilation and TradingView execution are required before calling the Pine implementation verified. Check representative order times, prices, stop/target behavior, costs and the identical date window against replay; investigate discrepancies rather than adjusting replay to improve agreement. Native funding limitations must remain visible in the report.

Finally, evaluate the frozen script prospectively in paper trading on Bitunix candles. Log every signal and fill, including skipped and canceled orders, and execution costs. Do not claim an improvement from a handful of winners or replace this forward step with another backtest. The proposed scope is research and implementation; live exchange orders require separate user instructions.

## Deliverables

- Frozen protocol, five candidate definitions and unchanged baseline comparison.
- Verified data manifests, complete trade logs, continuous equity, branch diagnostics and costs.
- One selected design or an explicit no-selection result; untouched historical stress results only after selection.
- A new Pine candidate only if the gates pass, with native verification status and remaining prospective evidence stated plainly.
