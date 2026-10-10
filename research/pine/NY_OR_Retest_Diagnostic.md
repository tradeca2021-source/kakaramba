# NY retest diagnostic variant

The main `NY_OR_Retest_Research.pine` now includes these diagnostics. `NY_OR_Retest_Diagnostic.pine` is an identical compatibility copy; use either for the next native export. Standard BITUNIX:BTCUSDT.P 15-minute candles, 0.07% commission per side, two-tick slippage and the original comparison dates are required. See BITUNIX_COMPARISON.md for the full protocol.

This variant only adds entry-comment and panel diagnostics. A normalized exact-source comparison confirms all eligibility rules, quantities, order prices, entry timing and exits remain the same as the reference. The strategy is still experimental; the original replacement criteria failed.

Each entry comment records planned entry (signal close, before next-tick fill), stop, target, estimated net R/R, estimated account risk percentage and frozen ATR. The panel displays the last observed actual-fill risk estimate and net R/R, including fills on trades that closed before the next chart calculation. Risk estimates include modeled fees, slippage and the existing ATR gap reserve; they are not guaranteed loss limits or realized PnL. Actual-fill warnings observe fills without retroactively canceling them.

Export the complete Strategy Tester XLSX. Compare actual fill prices with the planned entry, and recalculate payoff from the actual fill before deciding to change stops, targets or filters. Entry comments are metadata and should not change the tester's results; verify identical trades against the reference on identical data/settings. The diagnostic comments are not the v91 webhook format and should not be routed to an existing broker automation without a separate integration review.

Third-party parser validation only checks syntax; it does not establish TradingView compilation, builtin type compatibility or execution parity. Performance evidence still requires the native export. No new profitable threshold was selected.
