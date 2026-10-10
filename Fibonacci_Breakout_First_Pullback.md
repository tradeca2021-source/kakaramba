# Fibonacci Breakout First Pullback

Open `Fibonacci_Breakout_First_Pullback.pine` in TradingView's Pine Editor, save, and add to a BTC 15-minute chart. Default higher trend timeframe is 4 hours; it must exceed the chart timeframe. This is a new experimental hypothesis, not a profitable replacement established by the previous research.

Long rules (shorts mirror them):

1. A candle closes above a previously confirmed swing high. The previous **closed** higher-timeframe candle is above its EMA50 and that EMA is rising. One attempt per broken swing high.
2. Use the most recently confirmed swing low as the origin. Wait for a confirmed pivot high at/after the breakout candle, then freeze that endpoint, the 50% and 61.8% levels. The impulse must span at least 2 ATR. No backdated entries.
3. Trade only the first 50–61.8% pullback after endpoint confirmation. If any earlier candle after the endpoint already touched 50%, skip the setup. A close below 61.8%, a wick through the origin, an endpoint revisit, trend loss or 60-bar expiry cancels the setup.
4. Require a bullish candle intersecting the zone that closes back above 50%. A bounce above 50% without that rejection consumes the setup. A rejection failing sizing/payoff also consumes it.
5. Place a buy-stop one tick above the rejection high. It becomes eligible on subsequent ticks, not earlier within the rejection candle. Stop is below the lowest price of that first pullback, buffered by 0.15 ATR. Target is the frozen impulse high. Require at least 1.5 modeled net R after fees, slippage and the sizing gap allowance.
6. The unfilled trigger lasts three bars; cancel at bar close if a new pullback low appears, stop/target is reached, a candle closes beyond 61.8%, trend is lost or the setup expires. A live order can fill intrabar before a cancellation condition becomes known. Once filled, the bracket stays fixed through new pivots and trend changes.

Defaults: equity risk 0.25%, notional cap 95% of equity, no leverage, maximum 1 BTC, quantity step/minimum 0.001 BTC, fee 0.06% per side and two ticks slippage. Modeled cost inputs must match Strategy Properties. Adapt tick/quantity settings to your actual symbol. Small quantities are skipped. Gap fills can exceed modeled risk; the stop-gap allowance is a sizing estimate, not a hard loss ceiling. There is no averaging down, partial exit or trailing stop.

The yellow band is the frozen pullback zone; blue is a pending entry trigger; red is the fixed stop; green is the impulse-extreme target. The panel explains skipped/waiting setups and shows planned quantity/net R.

Local checks validate entry-predicate boundaries and the closed-HTF request contract. Native Pine compilation and TradingView backtesting are unavailable here. This version has not been historically validated. The July–September 2026 period used for earlier research is no longer an untouched validation period. Use a separate unused period for a profitability claim, with realistic fees, funding and venue-specific execution.

```sh
python3 -B tests/test_fibonacci_breakout_pullback.py
```

## v2: cancellation fix and entry diagnostics

Pending stop entries now cancel on a close beyond 61.8%, even when the buffered stop and the previous pullback extreme remain intact. This enforces the same close-based invalidation during both setup and pending-order states. Cancellation occurs at bar close; it cannot undo a fill earlier in that candle.

Trading filters, 1.5 net R, risk sizing and target remain unchanged. The diagnostics count the path through breakouts, confirmed impulses, first zone visits, rejections, submitted orders and observed fills. Skip counts distinguish geometry, cost-adjusted reward/risk and quantity failures. Additional counts show pullbacks missed before pivot confirmation, invalid setups and canceled pending orders. Counters apply to loaded chart history, not a separate Deep Backtesting date selection.

Optional BOS, REJ and ORDER markers show breakout confirmation, rejection evaluation and order submission. REJ may fail the payoff gate; ORDER is not a fill. TradingView's strategy trade markers identify actual fills. Yellow Fibonacci bands alone indicate a setup. If orders are zero, the stage and skip counts identify the binding rule before considering any parameter changes.

Six local checks pass, including a regression where an unfilled order is canceled solely by closing beyond the deep boundary. These checks do not establish native Pine compilation or profitability.
