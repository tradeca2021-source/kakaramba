# Next Bitunix comparison: structured NY opening-range retest

Use `NY_OR_Retest_Research.pine` from this directory as a separate strategy. It already implements a more structured entry alternative; no new performance claim or optimized parameter was added. It does not use the v91 news library or its webhook order format. It is for native backtest comparison, not a drop-in live automation replacement.

## Why compare this design

The uploaded v91 Bitunix five-minute export has 940 trades, net -40,631.75 USDT and profit factor 0.415. Its recorded net-R/R >= 1 subset still loses; adding arbitrary filters cannot establish an edge. Only 22 trades entered within 30 minutes of the preceding entry, so rapid repeats do not explain most losses.

The repository's pre-existing opening-range retest uses a defined session range and completed four-hour trend, a later first-touch rejection, one setup per New York date and a cash-close exit. Its archived Python study reports +1,375.94 USDT on 34 positions in 2021–2022 and +912.95 on 46 positions in January 2024–September 2026, in separate 100,000 USDT accounts after modeled costs and funding. These are Binance proxy-data results on inspected periods, not fresh Bitunix validation. They must not be combined into a portfolio return. The design failed the original replacement criteria and remains research-only.

## Run in TradingView

1. Create a separate Pine Editor script containing the complete `NY_OR_Retest_Research.pine`.
2. Use standard BITUNIX:BTCUSDT.P **15-minute** candles. The five-minute v91 chart is not supported by this fixed design.
3. Match strategy Properties to the fixed model: capital 100,000 USDT, commission 0.07% per side, slippage two ticks, margin 100%, Bar Magnifier enabled. Do not reduce the commission to make results look better. Pine cannot read Properties, so these must agree with its internal estimates.
4. Turn on Restrict entry dates and set the same available comparison dates as the original export. End is exclusive. Keep display timezone separate: the strategy explicitly uses America/New_York with daylight saving.
5. Export the full Strategy Tester XLSX, including trades and Properties. A small or zero sample is inconclusive, not a passing test.

The 09:30/09:45 candles form the opening range. Only a completed, trend-aligned breakout between 10:00 and 13:00 can arm a setup. Its first boundary touch must reject on one of the following four candles. Failed first touches consume the setup. The stop is beyond the opposite range edge with a 0.25 ATR buffer; target is a fixed 3R from the signal close, with a modeled net-R/R floor of 1.5. Entry and bracket submit together for next-tick execution. At 16:00 NY, a market-close command submits; brackets remain active until closed.

## Assess fairly

Compare net PnL, profit factor, drawdown, trade count, costs, monthly consistency and largest-winner concentration. This design uses 0.25% account risk versus v91's 0.15%, and 0.07% fees versus 0.06%. Raw dollar totals are therefore not a controlled entry-only comparison. Do not equate higher profits from larger sizing with better entries. The fixed research strategy has no input to change that risk; a common-risk/common-cost replay would be a separate experiment.

Pine excludes funding, unlike the archived Python study. Native intrabar fills, TradingView data coverage and Bitunix candles may differ. No profitability claim for Bitunix or live webhooks follows from the repository report. If results on this inspected year look better, they are development evidence; confirmation needs a genuinely unseen period.

## Current verification

All 22 existing session tests passed during this follow-up. They exercise the Python session engines and include causal range/retest sequencing and session behavior; they are not a native Pine compiler or Bitunix backtest. Native compilation and this specific comparison remain outstanding.
