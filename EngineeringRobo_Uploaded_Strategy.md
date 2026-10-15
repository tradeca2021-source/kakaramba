# Current display revision: SL TP Levels r5

The current source retains each submitted trade's SL/TP drawings and distinguishes pending projections from actual fills. It removes the old fixed screenshot prices. See `EngineeringRobo_Stop_TP_Strategy.md` for the current behavior; the older revision notes below are historical.

---

# Current version: per-trade stop and TP brackets

The current source is **EngineeringRobo - SL TP Reverse r4**. Its updated behavior and validation are documented in `EngineeringRobo_Stop_TP_Strategy.md`. The historical sections below describe earlier revisions; the latest revision replaces the moving, close-confirmed TP condition with fixed fill-anchored stop/TP orders. The preceding r3 source is preserved in `EngineeringRobo_TP_Reverse_r3_Backup.pine`.

---

# Strategy conversion of the newly uploaded indicator

Load EngineeringRobo_Uploaded_Strategy.pine as a new strategy, then open Strategy Tester. The source is the latest 6,094-byte uploaded indicator, not the previously integrated MNQ tester. All uploaded price levels, dashboard inputs/calculations and plotted markers are retained. The old unused SMA input and visual approximations are deliberately preserved rather than silently redesigned.

Confirmed main BUY signals enter Long; confirmed main SELL signals enter Short. Opposite entries reverse an existing position, with pyramiding disabled. Strategy order markers normally appear on the next bar because orders are generated after the signal bar closes and fill on the next available tick. No MNQ session, news, weekday, timeframe or FVG gates are included.

Order quantity defaults to one contract/share/unit and is explicitly passed to each strategy.entry. It is allocation sizing, not percentage risk sizing. Adjust it to the symbol's tradable minimum and your account capital. Strategy Properties default to USD 100,000 initial capital, 100% margin requirements, 0.07% commission per fill and two ticks slippage. Broker/venue charges and instrument sizing are not validated. For example, at MNQ 30,000 with point value $2, one contract requires roughly $60,000 under the selected 100% margin assumption, before costs. Smaller capital can cause rejection. Fractional input does not guarantee the instrument supports fractional contracts.

Enable BUY trades and Enable SELL trades default on. Disabling a direction blocks entry in that direction, but an opposite signal can still close an existing position. Signal direction defaults to Normal. Inverted (experimental) remains an explicit comparison option and changes both labels and main order direction. Boost markers are visual only. TP exits are always enabled. The profit marker retains the uploaded formula: a confirmed close reaches two current ATRs favorably from the most recent main signal close. It now requires a real position matching that signal direction. The marker and market close use the same `profit` condition; no phantom TP is displayed while flat. After TP, the strategy waits flat for the next main BUY/SELL signal. If an opposite main signal arrives before TP, strategy.entry reverses the position. If both conditions could occur on the same bar, the new main signal takes precedence. No separate stop loss or intrabar TP limit is added. A wick touching the distance alone is not a TP event; market exits normally fill at the following bar's open. The threshold uses current ATR, not a frozen ATR, and signal close rather than actual fill price, to preserve the uploaded marker's economics.

Dashboard markets do not filter entries. Dashboard formulas and limits remain as uploaded; preserving them does not validate them. Strategy alerts should use order fills with {{strategy.order.alert_message}}. Messages describe the target position/close event, not broker-ready quantity instructions.

Verification: uploaded visuals/dashboard preserved byte-for-byte after newline normalization; original Supertrend parameters preserved; the exact order-control block was exercised through a limited Python translation in 12 long/short/reversal/direction-disable/profit-exit cases. These checks do not compile Pine, load external market data, or simulate fills. Native TradingView compilation and Strategy Tester results remain unverified. No profitability or equivalence to the proprietary original is established.


Updated order-flow validation covers 14 extracted-source cases: long/short TP, no TP while flat, below-threshold prices, no repeated TP, no unconfirmed TP, both reversal directions, both flat-entry directions, disabled-direction closes, and waiting flat after TP. These are source control-flow checks, not native Pine compilation or fill validation. The displayed strategy title is EngineeringRobo — TP and Reverse Strategy.


## Direction correction after workbook audit

The uploaded workbook showed Swap BUY/SELL signals = On. Revision TP Reverse r2 replaces that checkbox with Signal direction, default Normal, while retaining an explicitly named Inverted (experimental) comparison option. A top-right readout shows the active mapping and actual position/closed-trade count. Normal uses an upward Supertrend flip for BUY/long and a downward flip for SELL/short. This addresses the audited direction-setting mismatch; it does not establish better performance.

Remove the prior instance and add the revised script as a fresh instance. Confirm Signal direction is Normal and the title reads EngineeringRobo — TP Reverse r2. Keep the same BITUNIX BTCUSDT perpetual, standard 15-minute candles, dates, one-unit quantity, commission and slippage for the comparison. Recreate any strategy alerts after changing source/settings.

The pre-change source is preserved as EngineeringRobo_TP_Reverse_Before_Direction_Fix.pine. That copy retains the old source default; reproducing the uploaded workbook additionally requires its saved On setting from the workbook Properties. The source backup alone is not a snapshot of TradingView's runtime settings. The live order-control block, TP condition, reversal precedence, sizing and cost assumptions were preserved. Fourteen extracted order/TP/reversal cases and sixteen signal-mapping combinations passed. New native results are required to compare performance with the losing inverted run.

## TP Reverse r3: distinguish signals from fills

AI BUY/SELL labels remain raw confirmed signals. Added FILLED LONG/FILLED SHORT labels use actual broker-emulator position transitions, including reversals, and POSITION CLOSED uses a transition from a nonzero position to flat. Neither entry label is generated merely because a raw signal appeared. Filled position quantity and Actual closed trade count are exposed in the status line/Data Window; input values are hidden there to make them readable, while the Inputs dialog remains available. Both the primary file and ASCII download contain the same revision.

Order timing remains next-available-tick, normally the following bar open. The new markers are bar annotations of observed position changes, not exact fill-price coordinates. They reflect the chart's execution context; Deep Backtesting can calculate a separate range and its trades may appear only in the strategy report. Use the List of Trades for the selected run to verify its executions. Eight extracted position-transition cases passed, alongside the existing fourteen TP/entry/reversal checks. Native verification of the new marker rendering remains outstanding.
