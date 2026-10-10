# Six new designs: none qualified as a better replacement

The experiments on 10 October 2026 found no new design that beats the existing Fibonacci baseline across both multi-year comparisons and meets the predeclared consistency requirements. No new Pine strategy is promoted. The active experimental baseline remains `Fibonacci_Live_Impulse_Pullback.pine` v3; its earlier-period losses still stand.

Every evaluation year here was previously inspected. These are exploratory comparisons, including post-hoc follow-ups after failures, not new validation. The code and rules were committed before each corresponding run, but that cannot undo selection bias from earlier experiments. Independent $100,000 accounts cover 2021–2022 and January 2024–September 2026; their profits must not be added as one continuous portfolio return.

## Account results after costs and funding

All designs use 0.25% modeled equity risk per entry, at most 95% equity notional and 1 BTC, 0.001 BTC quantity increments, 0.07% commission per side, two ticks of directional slippage, and a 0.25 ATR gap sizing reserve. Actual archived funding rates apply to carried positions, with the five-minute opening traded price as the mark-price proxy. Five-minute execution includes stops on entry subbars and adverse opening gaps. Actual-fill modeled risk can exceed submission risk; warnings are counted, not hidden.

| Design | Older positions / winners | Older net USDT | Recent positions / winners | Recent net USDT |
|---|---:|---:|---:|---:|
| Unchanged Fibonacci v3 reference | 31 / 8 | -737.26 | 38 / 16 | 3,955.55 |
| Daily 55/20 channel, 3 ATR initial stop | 11 / 5 | 33.87 | 17 / 8 | 596.27 |
| Daily RSI2 entry, RSI70/30 recovery exit | 34 / 24 | 498.68 | 41 / 24 | -170.45 |
| Same RSI entry, RSI90/10 recovery exit | 32 / 20 | 965.99 | 39 / 20 | -580.85 |
| Same RSI entry, SMA5 recovery exit | 35 / 25 | 352.98 | 43 / 27 | 265.41 |
| Same RSI entry, three-day exit | 38 / 19 | -181.32 | 46 / 20 | -808.89 |
| Four-hour 55/20 channel, 3 ATR initial stop | 64 / 24 | -386.79 | 94 / 30 | -755.91 |

The baseline references come from the unchanged continuous-account runs in [channel/development.json](results/channel/development.json) and [channel/historical.json](results/channel/historical.json). Their native TradingView and Bitunix parity is unverified.

**More winning trades did not imply greater account profit.** The daily RSI70 design won 70.6% of older trades and 58.5% of recent trades, yet the recent account lost money. RSI90 delayed exits and worsened recent net further. The SMA5 alternative had positive total net in both accounts and more winners than the baseline, but recent profit was $3,690.14 lower than the baseline. Its recent profit factor was 1.180, below the declared 1.2 minimum, and only two of four older half-years were positive. These facts do not support describing it as the requested stronger strategy.

The daily channel is also too sparse and dependent on its largest winner: removing that winner leaves each account negative. The intermediate four-hour channel loses in both periods. Cost stresses were run for every design, not only selected favorable cases; all stress logs are published.

## Holding-period diagnostics

Before interpreting the daily design, the previous four-hour 20-bar breakout was examined at three fixed holding horizons: four hours, one day and one week. These labels have no stop or portfolio sizing and can overlap. They are not simulated trades. Each breakout label is compared with nonbreakout labels in the same calendar quarter, direction and quintile of trailing ATR/price. Quarter matching is retrospective diagnostic work, never a live strategy signal.

| Period | Holding horizon | Matched events | Mean excess net R | 95% calendar-block interval |
|---|---|---:|---:|---|
| Older | 4h | 366 | 0.0083 | -0.0201 to 0.0372 |
| Older | 1 day | 366 | -0.0255 | -0.1070 to 0.0547 |
| Older | 1 week | 364 | -0.1955 | -0.4656 to 0.0965 |
| Recent | 4h | 546 | 0.0046 | -0.0243 to 0.0352 |
| Recent | 1 day | 546 | 0.0071 | -0.0734 to 0.0955 |
| Recent | 1 week | 545 | -0.0126 | -0.3091 to 0.3284 |

Twenty-eight-day calendar clusters preserve dependence within the longest seven-day labels; 2,000 deterministic draws use seed 20261010. All intervals include zero. They are exploratory, unadjusted for the three comparisons or previous research. These results give no clear measured advantage over the matched controls. Account-report uncertainty separately uses the existing seven-day-block daily-equity method and must not be confused with these diagnostic intervals.

## Frozen rules and reproducibility

- Daily channel/horizon rules: [macro_trend_protocol.json](competition/macro_trend_protocol.json), committed at `57dbcf4`; engine, diagnostics and checks committed at `bf87cb5` before outcomes. Full [report](results/macro_trend/report.json), event-level labels, position logs, funding and daily equity are in [results/macro_trend/](results/macro_trend/).
- Daily RSI70 experiment: [daily_reversion_protocol.json](competition/daily_reversion_protocol.json), committed at `21814ab`; engine and checks frozen at `e7c99ed`. It buys RSI2 below10 above daily EMA200 and shorts RSI2 above90 below EMA200. Stops freeze two daily ATR14 from the signal close; recovery exits execute at the next open, with a ten-day maximum holding rule. Full [report](results/daily_reversion/report.json) and cost-stress logs are in [results/daily_reversion/](results/daily_reversion/).
- Four follow-ups: [exit_followup_protocol.json](competition/exit_followup_protocol.json), committed at `013ab9a`; implementations and checks frozen at `c71f4a3`. The three reversion alternatives change only the declared exits, not the entry or sizing rules. All four fail the unchanged comparison gates. Full [report](results/exit_followup/report.json) and logs are in [results/exit_followup/](results/exit_followup/).

Daily designs use only completed UTC days assembled from complete contiguous fifteen-minute groups. Signals never use incomplete days. EMA/ATR/RSI smoothing is causal, with warmup before the evaluated account period. New implementations are separate from every previously frozen engine. Checks cover partial periods, future-price changes, exact RSI smoothing, both directions, protective stops, next-open exits, funding timing, timeouts and busy-signal discard.

Checksum-verified official Binance USD-M BTCUSDT archives provide the data. Signals aggregate from five-minute candles; three known discrepancies with official fifteen-minute bars in the recent archive range remain disclosed in the existing channel report. These probes do not use the quarantined Bitunix pages. Funding units here are the existing verified Binance archive format, not the unverified Bitunix snapshot rate. Venue prices, fees and native order paths can differ. Five-minute closing drawdown misses intrabar excursions, and stops cannot guarantee a maximum loss.

Reproduce into separate output directories without overwriting the published record:

```sh
python research/competition/macro_trend_study.py --output /tmp/macro-trend-repeat
python research/competition/daily_reversion_study.py --output /tmp/daily-reversion-repeat
python research/competition/exit_followup_study.py --output /tmp/exit-followup-repeat
```

Each report records source and archive SHA256 hashes. Reproduction reuses inspected years and does not create fresh evidence. The [data-access ledger](DATA_ACCESS_LEDGER.md) continues to mark these years as reused. A better replacement still needs a measured advantage after costs, meaningful robustness and native/prospective evaluation; this experiment did not find one.
