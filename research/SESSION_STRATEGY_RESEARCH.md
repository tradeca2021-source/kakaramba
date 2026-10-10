# NY retest research and native comparison Pine

The original New York opening-range retest is the strongest new session candidate in these five comparisons. It has positive total net after modeled costs and actual funding in both reused accounts, and more winning positions than the Fibonacci reference. It **does not qualify as a replacement**: recent profit is lower than the reference and only three of six recent half-year blocks are positive. All three machine reports retain `selected: null`; the criteria were not relaxed. Fibonacci v3 remains the active baseline.

A separate [research Pine script](pine/NY_OR_Retest_Research.pine) ports that original retest for native comparison. Its title and panel identify the failed replacement gate. Creating this research artifact does not promote a failed candidate. The [port decision](pine/NY_OR_RETEST_PORT_PLAN.md) records that distinction and the exact Python reference. Native TradingView compilation, execution parity and venue-exact profitability remain unverified.

## How to run the research Pine

Open `research/pine/NY_OR_Retest_Research.pine`, copy the complete file into TradingView's Pine Editor and use standard BTCUSDT 15-minute candles. The strategy clock explicitly uses `America/New_York`; the chart's displayed timezone does not change it. Commission must be 0.07% per side and slippage 2 ticks in native Properties to match the modeled assumptions. Initial capital defaults to 100,000 USDT. Trading parameters are fixed; optional date windows and display controls are separate.

The opening range is exactly the 09:30 and 09:45 bars. At 10:00, freeze its high/low and ATR 14; range width must be 1–4 ATR. Weekdays use the NY calendar, including daylight saving, rather than an exchange holiday calendar. The previous completed 4h close and rising/falling EMA 50 supply direction. Between 10:00 and 13:00, the first aligned closing breakout consumes the date. On one of the next four candles, the first boundary touch must reject with a directional body, close outside the boundary, and finish within half a range width beyond it. A failed first touch consumes the setup; no later retry or queued reversal.

The market entry executes on the next tick after confirmation. The protective stop is beyond the opposite opening-range edge with a 0.25 frozen ATR buffer. Target is three times signal-close-to-stop distance from signal close. Bracket and size freeze at submission. Minimum modeled net reward/risk is 1.5 after costs and gap reserve. Risk is 0.25% of equity, with 95% notional exposure and 1 BTC caps and 0.001 BTC lot increments. These are submission estimates, not guaranteed realized loss limits. Actual-fill warnings observe adverse prices without retroactively undoing orders. At 16:00 NY, the close command fills on the next tick; brackets remain active until the position closes. Optional comparison-end liquidation uses an immediate close as documented in code.

Pine excludes funding. The Python comparison includes actual archived funding settlements on carried quantity, using the five-minute opening traded price as the mark proxy. Native broker intrabar paths and Bar Magnifier coverage can differ from Python's conservative five-minute stop-first replay. A parser is a syntax check, not the TradingView compiler.

## Account comparisons

Every period was inspected before these experiments. The later projection and lifecycle hypotheses are explicitly post-hoc. Two independent continuous 100,000 USDT accounts cover 2021–2022 and January 2024–September 2026. Do not add their profits into one continuous portfolio return. All designs use the same risk/exposure/quantity caps and 0.07% per-side fee/two-tick slippage assumptions. Actual account fee tiers and Bitunix data are not verified here. No quarantined Bitunix API page supplies these results.

| Design | Older positions / winners | Older net USDT | Recent positions / winners | Recent net USDT |
|---|---:|---:|---:|---:|
| Fibonacci v3 reference |31 /8|-737.26|38 /16|3,955.55|
| NY direct close breakout |237 /98|-1,184.12|352 /152|-4,393.89|
| **NY first-retest, cash-close exit** |**34 /18**|**1,375.94**|**46 /26**|**912.95**|
| Same-candle 1.618 projection/local stop |17 /6|568.90|25 /6|-547.53|
| Two-candle 1.618 projection/local stop |33 /10|61.83|57 /17|-1,880.75|
| Original retest/24h timeout |33 /13|194.38|46 /14|-212.52|

The original retest has older/recent profit factors 1.463/1.295 and five-minute closing drawdowns 1.064%/1.661%. Net excluding each period's largest winner remains +$855.32/+$325.37. At 0.10% per-side fees, net is +$1,026.23/+$290.42; at 20 ticks slippage, +$1,320.46/+$778.93. Those stresses are on reused data, not independent validation. They can change which entries pass the payoff gate. Five-minute closing drawdown can miss intrabar losses.

The two Fibonacci projection variants and 24h hold reduced recent profit. Those outcomes are retained rather than used to select different projection ratios, timeouts or buffers. The original cash-close route misses the recent reference by $3,042.60 and misses the four-positive-block gate. Increasing winning-position counts from 8/16 to 18/26 is an improvement in that statistic, not proof of greater overall profitability. All account-report uncertainty intervals remain exploratory seven-day calendar-block resampling of daily log returns; reuse and multiple comparisons are not resolved by those intervals.

## Frozen experiments and full evidence

- [Opening-range protocol](competition/session_breakout_protocol.json): rules committed at `c317d8f`, engine/checks frozen at `5806263` before outcomes. [Report](results/session_breakout/report.json) and all position, funding and daily-equity files: [session_breakout/](results/session_breakout/).
- [Fixed Fibonacci follow-up](competition/session_fib_protocol.json): rules committed at `6343906`, engine/checks frozen at `7d88ae9`. [Report](results/session_fib/report.json) and complete failed comparisons: [session_fib/](results/session_fib/).
- [Single 24h lifecycle follow-up](competition/session_hold_protocol.json): rules committed at `933c468`, engine/checks frozen at `bc9a26a`. [Report](results/session_hold/report.json) and all logs: [session_hold/](results/session_hold/).

Every report records source and official-archive SHA256 hashes and candle-quality exceptions. Signals aggregate verified Binance five-minute archives into fifteen-minute candles. The three known recent discrepancies with official fifteen-minute archive bars are disclosed rather than hidden. Prior frozen engines remain unchanged.

The new Python checks cover IANA winter/summer clock differences, partial opening ranges/HTF periods, future-prefix invariance, first-touch consumption, exact retest life, next-open fills, active entry-subbar protection, cash-close settlement timing, conservative fixed projections, stale-target rejection, two-candle sequencing and exact 24h timeouts. The native file additionally undergoes third-party parser validation; compiler/runtime verification is not claimed. [Pine verification record](pine/verification.json) records the file hash and parser version.

Reproduce without overwriting the published research:

```sh
python research/competition/session_breakout_study.py --output /tmp/ny-session-repeat
python research/competition/session_fib_study.py --output /tmp/ny-fib-repeat
python research/competition/session_hold_study.py --output /tmp/ny-hold-repeat
```

Optional syntax reproduction uses an isolated environment: `python -m venv /tmp/ny-or-pine-parser`, then install `pynescript==0.3.0`, `antlr4-python3-runtime==4.13.2` and `click==8.5.0` with its pip. Run `pynescript parse-and-dump research/pine/NY_OR_Retest_Research.pine --output-file /tmp/ny-or-retest-ast.txt` with that environment's executable. The parser checks grammar and produces an AST; it does not type-check TradingView builtins, compile strategies or simulate broker orders.
