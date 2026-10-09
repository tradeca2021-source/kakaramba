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

## v2: opposing levels and entry diagnostics

The default **Opposing Fib handling** mode is now **Cap before nearest**. With opposing clearance enabled, find the nearest valid opposing 50% level ahead of entry, excluding expired Zig Zag setups and violated/extension Fibs. Levels behind entry do not block a forward target. Selection is independent of array order.

If that level lies before the desired objective, put the objective two ticks before it and recalculate modeled net proceeds. The capped target must meet the greater of the existing minimum net reward/risk and the new capped-target floor (default 1.0). If geometry or economics fail, reject the entry. The stop and risk budget are never tightened to make the cap pass. The 1.0 floor and two-tick buffer are unoptimized starting settings.

**Require clear path** rejects an obstructed objective without capping. **Legacy last/all** retains the previous loop for comparisons, including its order-dependent last-level behavior when the strict-all option is off. Turning off opposing clearance skips these obstacle restrictions; cost, position and account controls still apply.

The panel adds **Long setup** and **Short setup** reasons for the latest live swing per direction: waiting for a closed rejection, expired/already-traded swing, invalid entry/stop/target geometry, opposing level, insufficient net payoff, stop-distance limits, size constraints or optional filters. When some candidates qualify, it shows the eligible count and separately identifies the newest swing's reason. Account/direction gates can prevent candidate evaluation; the status row and “Not evaluated” message distinguish that case. These are current-bar diagnostics, not cumulative rejection counts or an account of every historical missed trade.

Native compilation and profitability of v2 remain unverified. Test a fresh instance and compare identical backtest ranges; Deep Backtesting results and the chart's visible historical markers need not share the same range. Fib-failure markers are observation-only and are not orders. The local test command now also checks obstacle freshness, order independence, both-direction caps and post-cap economics.
