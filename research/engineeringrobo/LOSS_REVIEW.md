# EngineeringRobo loss investigation

## What is established

The latest supplied screenshot reports 266 closed trades, 69 winners (25.94%), net PnL -$24,633.34, maximum drawdown $24,682.47 and profit factor 0.211, over the selected August 2–October 15, 2026 range. This confirms executions, not a failure to submit all orders. The r5 NOT FILLED annotations were unreliable visual matches; r6 corrected their bookkeeping without changing the entry/SL/TP order block. That change cannot improve the strategy's trading expectancy.

The only workbook supplied is for an older, different run: 23 trades, inverted signals On, and the prior close-confirmed TP/reversal exits. It is not a transaction export of the latest 266-trade fixed-bracket strategy. Its results must not be used to assert the latest run's stop/TP counts, commission total, signal mode or settings. Source defaults are known; runtime values for the latest run remain unconfirmed.

## Finding 1: costs severely reduce the bracket payoff

The current source defaults to a 2-ATR TP, 1.5-ATR stop, 0.07% commission each fill, two ticks of slippage and one BTC per trade. There is no entry check for whether the target remains economically worthwhile after costs.

For illustration only, assume an actual long fill at $81,000, tick size $0.10, point value 1, one BTC, the default distances and no gaps. Entry slippage is already included in that assumed fill. Charge commission on entry and exit prices, and two ticks of adverse stop slippage. These are payoff calculations, not a replay or an estimate of how often targets are hit.

| Signal ATR | Net if TP fills | Loss if SL fills | Win rate needed under this two-outcome model |
|---:|---:|---:|---:|
| $25 | -$63.44 | $151.07 | TP itself loses |
| $50 | -$13.47 | $188.55 | TP itself loses |
| $75 | $36.50 | $226.02 | 86.10% |
| $100 | $86.46 | $263.49 | 75.29% |
| $150 | $186.39 | $338.44 | 64.49% |
| $200 | $286.32 | $413.39 | 59.08% |

Before costs, the nominal 2/1.5 bracket needs about 42.86% winners in a pure TP-or-SL model. That ratio does not describe net trading economics when fees are a large fraction of the ATR. Actual strategy reversals add other possible exit payoffs, so none of these modeled breakeven rates is the actual observed run's exact requirement.

Ignoring tick rounding, for a long target at P + 2A and per-side fee c, target net is `2A(1-c) - 2cP` per BTC. At P=$81,000 and c=0.0007, ATR needs to exceed about $56.74 just for a filled TP to be net positive. For a short it is about $56.66. Merely exceeding that threshold does not establish a positive expected return.

Reproduce the illustrative table with:

```sh
python3 -B research/engineeringrobo/cost_sensitivity.py --entry 81000
python3 -B tests/test_engineeringrobo_costs.py
```

Funding, spread, liquidity, gaps and actual entry/exit fees are not independently verified. Confirm the actual Bitunix taker tier before changing commission settings. Zeroing fees to obtain a positive report would not establish a tradeable result.

## Finding 2: the latest observed win/payoff combination is inadequate

Using the displayed, rounded profit factor 0.211 with net loss $24,633.34 implies approximately $6,588 in winning-trade net PnL and $31,221 in losing-trade net PnL. With 69 winners and 197 losers, the implied average winner is about $95.47 and average loser about $158.48. Rounding in the displayed profit factor makes these estimates approximate.

Those observed average payoffs would require about 62.4% profitable trades to break even, compared with 25.94% observed. This is descriptive arithmetic, not a forecast. A trade with exit comment AI Take Profit can still count as a loser after fees. Therefore the screenshot's win rate cannot be treated as the TP-hit rate or used to infer that 197 stops occurred. A trade-level export is needed for that breakdown.

The raw Supertrend reversal rules are a visual reconstruction with no established edge. SMA20/SMA50, pivots, RSI-based Boost markers and dashboard trend readings do not filter the main entries in this version. Trading every flip can produce churning in sideways conditions; that is a hypothesis to measure, not a proven attribution from the screenshot. The separately tested EMA/bracket candidate also lost in its small shown sample, so there is no evidence to promote that filter as the solution.

## Finding 3: costs and loss tails already hurt the older exported run

The older workbook verifies -$2,417.41 net with $2,672.11 reported commissions. Adding back commissions gives only +$254.70, still including modeled slippage; this is attribution, not an achievable zero-cost result. Its 14 winners averaged $283.10 and nine losers averaged $708.99. Two losses totaled $2,905.78. Trades 5 and 8 had positive PnL before reported commission but negative PnL after commission. All three TP exits were net positive in that older sample.

The older workbook confirms both displayed trade directions, three TP closes and 20 opposite-signal reversals. It also shows Inverted signals On. The current source exposes Normal as the default, but the latest screenshot does not independently establish its runtime signal setting. Changing signal mode changes entries and exits; the inverted export cannot be transformed into a normal-mode backtest by negating PnL.

## What is not yet attributable

The latest 266-trade workbook is missing. The available screenshot cannot identify:

- TP hits that became net losses after costs, versus actual stop-outs and reversal exits.
- Actual commission total, average entry price and risk/target settings across the run.
- Long/short, duration and date concentration of the losses.
- Whether capital/margin rejected some other entries.
- Which candles touched both SL and TP and how intrabar fill ordering affected outcomes.

A List of Trades export can answer most of the first three questions and expose reconciliation issues. The corresponding Properties sheet is necessary to verify settings. Candle/lower-timeframe data is additionally needed to replay alternate exits or establish ambiguous intrabar event order. Favorable/adverse excursion summaries cannot identify that event order.

## Next investigation, before changing trading rules

1. Obtain the latest 266-trade XLSX, including Properties and List of Trades. Pair entry/exit rows once per trade so commissions and PnL are not double counted.
2. Reconcile net PnL and fees; group by exit reason, direction, date and duration; count net-losing TP exits and fee-flipped winners; inspect the largest losses.
3. Confirm actual fee tier, signal mode and chart/backtest settings. Compare configurations on identical periods and costs.
4. Only then test a predeclared change that addresses the measured problem, such as cost-aware entry eligibility or a different exit design. Increasing TP may reduce hit rate; widening the stop increases loss size. Neither is established as a fix. Smaller order size reduces cash exposure but does not improve percentage expectancy under proportional costs.
5. Keep this inspected period as development evidence. Do not repeatedly tune it and describe it as fresh validation; evaluate the selected design on a separate chronological sample.

No strategy parameters or order rules were modified during this investigation. Seven arithmetic tests validate cost treatment, long/short exit fees, slippage, tick rounding, invalid inputs and quantity scaling. They do not validate Pine execution, alternative strategies or profitability.
