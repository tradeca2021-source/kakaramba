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

## v3: bounded two-candle reclaim and chart decisions

By default, the first zone-touch candle or the immediately following candle can supply the directional close back across 50%. The following candle does not need to touch the zone again. The pullback extreme includes both candles, so the fixed stop remains outside the observed pullback. Failure to reclaim by the second candle consumes the setup. Turn off “Allow next-candle midpoint reclaim” to require confirmation on the first touch candle; this is not a restoration of v2's potentially longer waiting period.

Decision labels show ORDER or the specific rejection failure and calculated net R. Toggle “Label rejection decisions” to hide them. Fees, net-R minimum, quantity caps and first-pullback discipline remain intact.

A full BOS-specific approximate execution audit is available in `research/results/bos_v3_execution_audit/`. On previously inspected January–September 2026 Binance data, v2 produced 11 trades / $1,351.83 net; v3 produced 8 trades / $2,009.74 net, starting with $100,000. The bounded confirmation window removes some later entries, so this is not just a relaxation that forces more trades. Neither result constitutes new untouched validation. Eight trades cannot establish a reliable edge; v3's July–September realized result was negative and it traded only once in those months. Do not interpret the full-period profit as evidence of consistent monthly profitability.

The model uses prior closed 4-hour candles and resting stop-entry orders eligible after rejection. Stops and targets are frozen. It conservatively checks the whole entry candle for stop/target touches, even if the extreme preceded entry, and omits spread/funding. Native TradingView fills may differ. Nine local checks cover entry predicates, bounded two-candle eligibility, pending invalidation, causal HTF values and next-bar stop-entry timing.

```sh
python3 -B tests/test_fibonacci_breakout_pullback.py
python3 -B tests/test_breakout_execution.py
python3 -B research/breakout_pullback_backtest.py
```

## v4: audited costs and consistent competition windows

v4 keeps the v3 stop-entry logic. The eight-candidate comparison and subsequent limit-entry experiments did **not** establish a validated upgrade. Read the complete [competition research](research/results/competition/README.md), including the failed independent holdout and rejected higher-frequency variants.

The default Strategy Properties commission is now **0.07% per side**: exchange-fee assumption 0.06% plus 0.01% execution reserve. Both the net-R eligibility check and position sizing use their sum. Set Properties commission to the sum if you change those inputs; Pine cannot read Properties overrides. This is a conservative spread/execution allowance, not observed spread. Native strategy PnL excludes funding, while the external research applies actual funding rates with a mark-price proxy.

Optional “Restrict entry and exit dates” warms indicators/pivots on prior bars but starts no setups outside the chosen window. The start is inclusive; signals closing at the exclusive end are disallowed. Pending entries cancel and open positions close at the end. It remains off by default. Use the same dates in Deep Backtesting, and enough prior candles for stable indicator history. The script cannot control TradingView's Deep Backtesting selector.

The panel adds chart-run net profit/PF, modeled cost per side and explicit window/loaded-start dates. Chart-run counters and PnL may differ from a separately selected Deep Backtesting run. No signal-frequency changes, widened stops, leverage increases or extended targets were added to improve the headline score.

18 focused local checks pass across the Pine predicates, the prior execution audit and the new funding-aware 5m engine. Native Pine compilation and venue-exact trading performance remain unverified. Current status: experimental, no variant earned validated promotion.

## v5: optional bounded stop-limit entry

The default remains v4's rejection-high/low stop entry. Enable **“Cap adverse entry price with stop-limit”** to activate a stop-limit order. For a long, the rejection high must break before the buy limit becomes active; for a short, the rejection low must break before the sell limit becomes active. This is different from immediately placing a retracement limit after rejection.

The cap is the most adverse entry price satisfying the selected minimum net R after modeled commission/reserve, two-sided slippage and ATR gap allowance. Long caps round down; short caps round up. Position size uses that worst entry, and notional sizing uses the larger of trigger and cap. The bracket is fixed. A gap beyond the cap can leave an activated order unfilled until it retraces; original expiry and close-based invalidations still cancel unfilled orders. The aqua line shows the pending cap.

This bounds entry price, not total loss. Stop gaps, funding, unknown fees and execution can still exceed modeled risk. Improved sell-limit gap fills can also exceed the notional sizing estimate; cash/margin rules remain the broker constraint. Pending cancellations happen at bar close and cannot undo an earlier fill. Pine native stop-limit/bar-magnifier behavior still needs verification.

The [execution audit](research/results/competition/stop_limit_audit.json) compares the same seven previously inspected independent-account periods. Both modes took 23 trades. Ordinary stop entry totaled $2,957.97; capped entry totaled $2,399.85. Sum of period closing drawdowns declined from $3,077.03 to $2,464.81, largely because sizing at the adverse cap reduced quantities. These sums are not one continuous account's return/drawdown. Capped entry did not improve profit and has not passed fresh validation, so it stays **off by default**.

22 focused local checks cover entry/cost/date formulas, cap algebra and geometry, long/short stop-limit activation, adverse gaps that remain unfilled, later retrace fills, normal trigger crossings, funding and causal execution. The feature is an optional execution control, not a promoted trading-edge change.

```sh
python3 -B tests/test_fibonacci_breakout_pullback.py
python3 -B tests/test_competition_engine.py
python3 -B tests/test_breakout_execution.py
python3 -B research/competition/stop_limit_study.py --output /workspace/fib-gap-audit
```

## v6: experimental breakout-quality options

“Breakout quality (experimental)” defaults to **None**, preserving v5's default signals and entries. Four modes are available:

- **None:** original confirmed breakout cross.
- **Displacement:** directional candle body >=0.5 ATR, close within the directional outer 25% of its range, and close >=0.1 ATR beyond the broken confirmed swing.
- **Fresh origin:** the confirmed opposite pivot used as the impulse origin must be 1–40 chart bars old at breakout. On a 15m chart, the maximum is 10 hours from the pivot's occurrence, not its later confirmation.
- **Both:** require both conditions.

The checks run on the closed breakout candle, using pivots already known before that candle's newly confirmed pivots. Rejected crosses do not consume the swing identifier, but a later entry still requires a genuine recross; a strong follow-through already above/below a broken level cannot become a backdated breakout. Stops, targets, costs, sizing and first-pullback rules remain unchanged. The gray FILTER marker and panel count explain rejected crosses when a filter is enabled.

The [quality audit](research/results/competition/breakout_quality_audit.json) uses seven previously inspected independent-account periods. None: 23 trades, $2,957.97 aggregate net, PF2.140. Fresh origin: 22 trades, $3,183.75 net, PF2.342. The gain is mostly one skipped $222.52 loss plus subsequent sizing effects. Displacement/Both: 17 trades, $2,883.36 net, PF2.670. The July–December 2025 losing period remains unchanged for every filter. These results are exploratory, not fresh validation, and none is promoted as a validated default.

For an explicit TradingView paper comparison, select **Fresh origin** and keep all other settings/date windows the same. Match 0.07% commission/reserve and the same chart history. It is a candidate to test, not a proven profitable upgrade. Native Pine compilation and Bitunix results remain unverified.

26 focused checks now include the actual Pine displacement/freshness/mode expressions and matching simulator boundaries. Thresholds were fixed in the [protocol](research/competition/breakout_quality_protocol.json) before running this experiment; no grid search or threshold retuning was performed.

```sh
python3 -B research/competition/breakout_quality_study.py --output /workspace/fib-quality-audit
```
