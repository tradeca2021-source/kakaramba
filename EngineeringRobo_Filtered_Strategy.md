# EngineeringRobo filtered bracket candidate

Experimental comparison candidate; no performance improvement has been demonstrated. The working baseline remains EngineeringRobo_Uploaded_Strategy.pine. A user-provided screenshot of that baseline reported 22 trades, 7 winners, -$5,174.41 net, $5,801.78 maximum drawdown and profit factor 0.337. Those are screenshot observations from the selected run, not independently reproduced results.

## Changes to test

- New long entries require price above a rising EMA50; shorts require price below a falling EMA50. This can be disabled to isolate the exit changes.
- TP distance is two ATRs, captured at the entry-signal bar and rounded up to whole ticks. Pine's relative `profit` argument anchors this distance to the actual simulated fill price. Subsequent ATR changes cannot move the target.
- A protective stop is 1.5 signal-bar ATRs away, rounded up to whole ticks, using the relative `loss` argument. It can be disabled to isolate this change. Stops are not guarantees of maximum loss across gaps.
- Bracket orders are submitted alongside their entry orders, rather than waiting until the fill bar closes. This changes execution semantics from the baseline's close-confirmed profit marker: a touched target can fill intrabar under the broker emulator's assumptions.
- Opposite signals still exit an open position. Reversal happens only when the proposed new direction is enabled and passes the trend filter; otherwise the strategy closes and waits flat.
- TP markers now reflect actual simulated exits with the AI Take Profit comment. They do not show hypothetical profit-distance events while flat. Boost signals remain visual only.

The Supertrend settings, fixed order quantity, capital, margin, fees, slippage, no-pyramiding behavior and dashboard are inherited. The baseline file has not been edited. Candidate parameters are manually chosen hypotheses, not fitted or optimized values. EMA length 50, TP 2 ATR and stop 1.5 ATR need validation and are not recommendations supported by performance evidence. EMA filtering may miss profitable countertrend moves; stops may increase churn or lock in losses.

## Compare fairly

Use the same standard-candle symbol/venue, timeframe, date range, initial capital, order quantity, commissions and slippage for both scripts. Confirm actual trades executed. The baseline's screenshot alone cannot identify the best fix: export its List of Trades and preserve the corresponding Properties and date range. Run the candidate in Strategy Tester and export that run too.

Predeclare these four comparisons before inspecting their results: candidate with filter off and stop off (isolates fixed fill-based TP), filter on and stop off, filter off and stop on, and filter on and stop on. Keep the specified lengths and distances fixed. Compare net after costs, maximum drawdown, profit factor, trade count, exposure and dependence on a few trades. Do not call higher net alone a win if risk increased materially or the sample is tiny. Then test on a separate chronological period not used to select the configuration; earlier repository research periods already inspected are not fresh validation. Do not repeatedly tune the same losing seven-day window and call it validation.

## Verification limits

Source-derived checks exercised seven order/bracket cases and eight EMA-filter cases, including both entry directions, eligible reversal, blocked-direction closes, optional stop removal, tick rounding, missing signals and fixed-distance assignment. The original baseline source remained intact. These checks translate a limited source subset to verify branch and argument wiring; they do not compile Pine, reproduce historical fills, prove order timing in TradingView, or establish profitability. Native compilation and comparable backtests remain outstanding.
