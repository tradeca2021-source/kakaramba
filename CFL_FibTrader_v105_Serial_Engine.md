# CFL v105: replacement serial engine

Use the complete `CFL_FibTrader_v105_Serial_Engine.pine` file. Replace v104 rather than adding another instance, and reset saved inputs. v105 is a 234-line replacement of the prior roughly 1,500-line multi-engine implementation. Earlier files remain available. This is an explicit, testable reconstruction hypothesis; it is not recovered original source or verified screenshot parity.

## Lifecycle

1. Seed one active series from the configured origin or the first eligible candle. Origin is 100%; terminal is 0%. The terminal follows directional wick extremes while the series develops. Distance scaling is locked at series birth, so changing price cannot move freeze/stop thresholds underneath the same series.
2. A completed candle must retrace at least the greater of the configured point pullback and 23.6% of the series range to freeze its terminal. The leg must also meet MinMove. Freeze confirmation happens before order eligibility; there is no extra reaction requirement at the midpoint.
3. Quote a blind limit at the front-run 50% level while close is on the approach side. Target defaults to retracement label 38.2%; stop defaults to 61.8% plus one adverse tick. Once frozen, all three prices stay fixed. One actual fill consumes the series, including a same-bar entry/exit. Quotes alone do not consume it. A completed trade does not create another series or reset its used flag.
4. Interior price oscillations and a wick through the origin do not create opposite Fibs. A CLOSE beyond the origin ends the series and starts one opposite series from the previously known terminal to that close. Origin invalidation takes priority over extension completion on a wide candle. No assumed high/low ordering or retroactive opposite wick is used.
5. A CLOSE reaching the configured negative extension (default -38.2%) of a frozen series ends it and starts one continuation from its terminal to that close. A new series cannot quote on its birth candle. Developing series do not reset merely because their moving terminal extends.
6. Filled trades retain the stop/target snapshot submitted with their entry, including when the active Fib resets or reverses. There is no opposite-signal market exit.

These choices deliberately replace concurrent nested/continuation branches and the separate swing tracker. One active series means there is no second live opposing Fib to evaluate: the old opposing-midpoint filter and multi-series selection inputs are removed. Original concurrent inner series, exact anchor/reset behavior, the distinct FrontRunOfPt input and original sizing remain unverified. A serial model cannot claim to reproduce every nested-series behavior discussed with the original screenshots.

## What is visible

Each meaningful developing series creates a connected entry-to-stop staircase. When levels move, the old segment ends and the next begins at the current observation bar; earlier boxes are not rewritten. The zone ends on a close through its stop boundary or a series reset. Last 400 segments are retained by default (maximum 440). Historical level plots remain beyond that archive; they are line plots, while boxes supply the stepped zones. Lines have a missing sample on reset to separate series. Gold -23.6% remains a labeled context level, separate from the actual target.

The status panel reports the current direction, developing/frozen phase, exact origin/terminal, last reset reason, and why entry is armed or blocked. Native TradingView fill markers remain actual orders. No simulated markers are added to suggest trades that did not execute.

## BTC execution

Fractional sizing, a default 0.10%-of-equity modeled risk budget, maximum one BTC and 100%-of-equity notional cap remain. Quantity rounds down to the configured step and is rejected if below the minimum. Modeled commission/slippage and the extra stop-gap allowance enter sizing. Strictly positive target proceeds after costs are mandatory; the optional minimum modeled net reward/risk defaults zero. Account gaps, funding and spread can cause different outcomes. Match modeled fee/slippage inputs to Strategy Properties, and verify contract quantity/point-value conventions for the chosen symbol.

The old futures TargetLossInTicks sizing and research presets are removed from this file. v104's risk correction is retained as BTC account sizing rather than presented as recovered original behavior. Narrow 38.2% targets may still be rejected or economically unattractive on BTC at 0.06% commission per side. This engine does not lower costs or widen targets to manufacture trades.

## Verification

Run `PYTHONDONTWRITEBYTECODE=1 python tests/test_cfl_v105_serial_engine.py -v` from the repository root. Eighteen tests evaluate the actual extracted Pine transition/risk expressions and source wiring, with 300 varied risk-sizing cases. Cases cover mirrored terminal development/freeze, wick vs close origin breaks, continuation expiry, single-series identity through oscillation, filled-bracket preservation, prior-state stability, scaling, fee-negative targets and quantity/exposure/risk bounds. The surrounding contract runner is Python, not the Pine broker emulator.

The third-party pynescript 0.3.0 parser completed successfully. Native TradingView compilation, trade-count reduction, profitability and original signal matching remain unverified. Review this version against the same BTC symbol/timeframe/history as prior results; changing loaded history changes an automatic seed.
