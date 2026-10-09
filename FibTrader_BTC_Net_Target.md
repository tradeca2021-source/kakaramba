# BTC Zig Zag net-target comparison

Add `FibTrader_BTC_ZigZag_Net_Target.pine` as a fresh TradingView instance. Keep the existing risk-controlled version for comparison. This version preserves the 50% rejection entry, original Fib stop, fractional sizing, exposure limits and daily loss control.

The original 50% -> 38.2% geometry pays only 11.8% of the swing range before front-running adjustments. For the approximately 190-point leg visible in the supplied screenshot, that is about 22 points of gross reward versus roughly 97 points of round-trip fees per BTC at 0.06% per side and an 80,900 price. Rejection-close entries differ from the exact 50% price, but the fixed target remains narrow. The cost filter can therefore reject the setup even when a later rally looks attractive.

## Target modes

- **Net risk multiple (default):** solve for a target price that pays 1.5 times the modeled stopped risk after estimated fees and two-sided slippage. Modeled risk includes the existing stop-gap sizing allowance. Long targets round up; short targets round down to preserve the modeled reward floor. The target may lie beyond the original swing extreme.
- **Swing extreme:** use the frozen 0% swing extreme as the objective.
- **Original Fib:** retain the prior target-level input, default 38.2%, and target front-running ticks.

The selected objective is frozen on order submission and displayed separately for the open trade. Ordinary Fib labels remain reference levels. Stop distance, candidate expiry, opposing-Fib clearance, position sizing and account risk controls still apply; this does not guarantee more trades.

The existing exit mode remains **Bar-by-bar trail** by default. In that mode, the selected objective activates trailing rather than closes the position at a fixed take-profit. Select **Fixed target** if you want the objective used as a resting take-profit. Compare exit modes separately from changing target mode.

1.5 is an unoptimized starting objective. A larger objective can reduce the win rate, increase holding time and perform worse. The earlier uploaded export does not backtest this change. Market gaps can change the achieved reward/risk; funding and spread remain unmodeled.

## Validation

Run `python3 tests/test_fibtrader_net_target.py`. The checks evaluate actual Pine target arithmetic across long/short scenarios, verify directional rounding and confirm that sizing, swing detection and filled-exit code were preserved. They are not a native Pine compiler or market simulator.

Native compilation and profitability remain unverified. In TradingView:

1. Use identical symbol, timeframe, history, actual fees/slippage and margin for comparisons.
2. Compare Original Fib, Swing extreme and Net risk multiple with the same entry/exit settings.
3. Compare separate periods and both directions; include trade counts, net profit, drawdown and results excluding the largest winner. Do not choose a mode based only on the total profit.
4. Export the updated Properties and Trades sheets. OHLCV or chart replay is needed to evaluate missed setups and tune entry logic; screenshots alone cannot establish improved expectancy.
