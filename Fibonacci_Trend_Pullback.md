# Fibonacci Trend Pullback v1

A standalone Pine v6 strategy built independently of the earlier FibTrader variants. It has no library dependencies and does not alter the previous strategies. The defaults are unoptimized starting settings for BTC perpetual charts, with fractional BTC quantity units.

## Trading rules

1. Confirm alternating swing lows/highs with five left and five right bars. Confirmation is delayed: a historical pivot is known only when its right-side bars have closed. If a high and low confirm on the same calculation bar, skip both rather than assume their ordering.
2. Use a chronological low-to-high impulse for a long or high-to-low impulse for a short. Require at least five bars between endpoints and a range of at least two current confirmation ATRs. Freeze the impulse and all Fib prices when it becomes a candidate. A newer impulse supersedes an unsubmitted candidate; same-type tracker updates affect future impulses only.
3. With trend alignment enabled, require fast EMA 50 above slow EMA 200 and price above the slow EMA for longs; shorts mirror this. Wait for enough bars to initialize the slow EMA.
4. Require a closed candle to touch the tick-rounded 50% retracement, close back on the continuation side and have a directional body. Its close must remain inside the shallow 38.2% boundary; do not chase a rejection that already ran away. A rejection on the confirmation candle is permitted because all information is known at that candle's close. No signal is backdated to the pivot.
5. Submit a market order for the next available tick. One submission per impulse; never retry that impulse after submission. Skip candidates after 30 bars, a close beyond 61.8%, a stop crossing or a close beyond the impulse endpoint before entry.
6. Stop beyond the swing origin, with a 0.15 ATR buffer (at least one tick). Target the 127.2% extension measured from the origin. This is a fixed bracket, not a trailing exit. New pivots and trend changes do not move an open trade's bracket.

## Account controls

- Default commission: 0.06% per side; slippage: two ticks. These are illustrative, not verified Bitunix rates. Match the modeled inputs and Strategy Properties to your actual venue costs.
- Default equity risk: 0.25% per trade. Include estimated fees at entry/stop prices, two-sided slippage and an additional 0.25 ATR stop-gap sizing allowance.
- Quantity step/minimum: 0.001 BTC; maximum: 1 BTC. Round down and skip sub-minimum trades rather than force a minimum quantity. Also cap notional at 95% of equity, with 100% margin in Strategy Properties. The remaining exposure allowance is not a guarantee against gaps or rejected orders.
- Require positive modeled target proceeds and at least 1.0 net reward per unit of modeled stopped risk. The target is not extended or the stop tightened to make a bad candidate qualify.
- Default daily equity cutoff: 1%. It includes realized plus open PnL and resets at the symbol's exchange-calendar day. At rollover, use the previous bar's equity mark. The cutoff cancels entries and requests position closure at a calculation tick; it does not guarantee an intrabar maximum loss.

Quantity is sized from the rejection close before the next-tick market fill. Gaps, funding, spread and changed fee rates can exceed the model. Different markets require their own quantity settings and point-value verification.

## Chart and dates

The yellow band is the 38.2%–61.8% pullback area; the bold yellow line is 50%, red is the structure stop and green is the fixed extension target. Triangles indicate accepted rejection signals, while TradingView's native markers indicate actual fills. The panel reports the latest candidate reason, estimated net R, planned quantity and chart-run trade count.

Date restriction defaults OFF. Optional start/end inputs gate entries while allowing pre-window swing warm-up. The end is exclusive: do not submit a signal from a candle closing at or after it. Cancel orders and close positions at the available end-boundary calculation; bars gapping over the boundary can process later, and earlier market orders may fill before cancellation. Pine cannot change the separate Deep Backtesting date selector. Match dates and loaded history when comparing results.

## Validation

Run `python3 tests/test_fibonacci_trend_pullback.py` from the repository root. It checks actual Pine sizing/fee/rejection/trend/date expressions and representative risk/exposure bounds. It is not a native Pine compiler or broker emulator.

Native TradingView compilation and profitability remain unverified. Add the full script as a fresh instance and first verify compilation, symbol quantity units, fees, slippage, margin and normal candle type. A 15-minute BTC chart is a reasonable first comparison, not a proven optimal timeframe. Keep the same history/settings when comparing against earlier scripts. Evaluate both directions, separate periods, net profit, drawdown, trade counts and sensitivity to the largest winners. Do not infer a trading edge from local formula checks.
