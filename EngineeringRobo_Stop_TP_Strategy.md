# EngineeringRobo: SL TP Levels r6

Paste `EngineeringRobo_Stop_TP_Strategy.pine` into TradingView Pine Editor, save, and add a fresh chart instance. Confirm the title is **EngineeringRobo - SL TP Levels r6**. This is an independent reconstruction, not the original proprietary EngineeringRobo indicator. Native Pine compilation and rendering of this revision remain unverified.

## Orders

Confirmed Supertrend direction changes generate main BUY/SELL signals. BUY enters long; SELL enters short. Signal direction defaults to Normal; Inverted (experimental) explicitly swaps the signal mapping. Both directions are enabled by default. Super Boost markers are visual only.

Each accepted main entry receives a bracket submitted alongside the market order:

- Stop loss defaults to **1.5 signal-bar ATR14**.
- Take profit defaults to **2 signal-bar ATR14**.
- Distances round up to whole ticks and remain fixed for the trade.
- Relative `strategy.exit` distances anchor to the actual simulated fill price.

Adjust the distances under **Per-trade stop and take profit**. Market entries normally fill at the following bar open. SL/TP orders can fill intrabar; a candle touching both levels depends on TradingView's broker-emulator assumptions. Gaps can cause stop fills worse than the displayed level. Initial-fill-bar brackets are submitted without waiting for position detection on the next calculation.

An opposite signal reverses an open position and captures new bracket distances. A disabled opposite direction closes the old position without opening the disabled side. After SL or TP the strategy waits for a new main signal. Same-direction signals do not reset an open trade's levels. There are no inherited MNQ session, news or timeframe entry gates.

## Trade drawings

Each submitted entry creates dotted projected levels and a label saying **SUBMITTED / fill pending**. Gray is entry, red is SL, lime is TP. Pending projections use the signal close because the fill is not yet known; they are not absolute broker orders.

After matching actual open/closed trade records, drawings become solid and use recorded fill prices. Open lines extend right. Closed lines end at the recorded exit and remain visible, with entry/SL/TP prices and the exit reason in their label. Unmatched plans remain dotted and say **FILL UNMATCHED / check trade records**. This is a drawing-reconciliation status, not proof that an order was rejected.

Closed-trade records recover trades that open and close within one candle, even when the end-of-bar position is flat. Such trades receive a minimum one-bar-wide drawing for visibility; this does not mean they remained open for another bar. Multiple exits on a bar can produce only the latest custom exit marker; use List of Trades for every execution.

**Trade level history** defaults to 30 plans, adjustable from 1 to 100. Older drawings are deleted at that cap, including unfilled plans. Plans match by direction and recorded entry timestamp. Known fills are matched first; otherwise the latest eligible signal at or before the entry time is used. Plan registration precedes reconciliation, so same-bar entry/exit records can be matched. Drawings use time coordinates rather than assuming identical chart bar indices. Native matching still requires verification. Deep Backtesting can use a different range from chart-visible history.

The old fixed BTC screenshot levels have been removed. Optional pivot context lines are gray, disabled by default and explicitly named support/resistance context.

## Sizing, costs and alerts

Defaults are one contract/share/unit, USD 100,000 capital, no pyramiding, 100% margin, 0.07% commission per fill and two ticks slippage. Quantity is fixed allocation, not a percentage risk budget. Instrument minimum size, capital and margin can prevent fills. Confirm costs and funding assumptions for the intended venue. Price-distance targets are before costs; no profitability improvement is established by these changes.

For strategy alerts, select order fills and use `{{strategy.order.alert_message}}`. Messages describe direction and exit events rather than broker-ready transaction quantities. Recreate alerts after script changes.

## Verification

Source-derived checks passed 13 order/bracket scenarios, six active-level calculations, four timestamp-drawing geometry scenarios and ten timestamp/plan-matching cases. They cover both entry/reversal directions, disabled directions, invalid ATR, same-direction repeats, tick rounding, fixed distances across ATR changes, gapped fills, shorts, same-bar closure and closed-history finalization. ASCII-only content and source delimiter checks also passed.

These are limited source-expression and argument checks, not Pine compilation, native fill simulation, or a historical profitability test. Earlier screenshots/exported results from prior strategy revisions do not validate this revision. Compare the same symbol, timeframe, dates, order quantity and costs in Strategy Tester and inspect its List of Trades.


## Correction from r5

The user supplied a report showing 266 closed trades alongside many NOT FILLED drawings. That proved those labels were not reliable evidence of rejection. r5 required the entry bar index to be strictly later than the signal bar and processed fill records before registering the current bar's plan. r6 removes those assumptions and accepts matching timestamps on the signal bar, while giving already-known fills priority over new pending plans. Older unmatched plans remain available to match later records until removed by the history cap. Reconciliation occurs before unmatched plans are visually retired, and the history cap is applied last. These are visual bookkeeping changes; the prior screenshot's -$24,633.34 result and 0.211 profit factor are not improved or invalidated by them. Native validation of the corrected drawings remains outstanding.
