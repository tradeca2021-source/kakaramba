# Fibonacci strategy: start here

There is currently **no strategy in this repository verified profitable across the reserved historical test and native TradingView execution**. The new channel design improved development profit but failed historical validation; the existing Fibonacci baseline also lost in that older test.

The active experimental baseline is **[Fibonacci_Live_Impulse_Pullback.pine](Fibonacci_Live_Impulse_Pullback.pine)** (v3). Other Pine files are earlier designs or research artifacts. The Pivot3 Research candidate failed its chronological confirmation, is visibly marked REJECTED, and is archived in `research/rejected/`.

1. Load the active script on **standard BTCUSDT 15-minute candles**.
2. Select **Baseline BTC 15m (experimental)** in Settings → Inputs → Profile.
3. Check the banner: **pivot5 / trend240m EMA50 / impulse2ATR / filterNone**. The profile also fixes the modeled costs, minimum netR1.5 and 0.25% account risk. Custom setup/risk input values are ignored in baseline mode, including stale saved settings.

The profile requires a15m chart. To experiment with other settings, explicitly choose **Custom (unverified)**; the visible status changes accordingly. Date windows and chart display controls remain adjustable. Native strategy Properties are separate: the default0.07% commission and2tick slippage must match the modeled assumptions. Funding is excluded in Pine.

Rejection decision labels default off to reduce chart clutter; fill warnings stay on. Actual-fill diagnostics show whether execution consumed the intended reward margin or exceeded modeled risk. They observe fills and do not undo orders.

The strongest current known-period result is38 completed positions /16 winners /+$3,932.89 summed across seven independent account periods. Several periods lose and one has zero fills. This is repeatedly inspected Binance research data, not fresh validation or a verified Bitunix/TradingView result. Native Pine compilation has not been available in this environment.

See [strategy rules and limitations](Fibonacci_Live_Impulse_Pullback.md), [tuning results](research/results/competition/TUNING.md) and [enhancement comparisons](research/results/competition/ENHANCEMENTS.md). Full research protocols, trade-level outputs and execution tests are included in the repository.

Seventeen additional structural alternatives are recorded in [STRUCTURAL_RESEARCH.md](research/results/competition/STRUCTURAL_RESEARCH.md). None passed the declared qualification conditions, so no unproven trading default was promoted.

The next five [regime designs](research/results/regime/README.md) also failed. A separately predeclared [four-hour channel follower](research/results/channel/README.md) made +$7,649.64 on 195 positions versus the baseline's +$3,955.55 on 38 positions over one continuous 2024–September 2026 account history. After source freeze, its reserved 2021–2022 test lost $2,583.90; the baseline lost $737.26. The channel failed both higher-cost tests and is research-only Python, not a new Pine recommendation. All code, trade logs, funding, daily equity and failures are published. [Data access history](research/DATA_ACCESS_LEDGER.md) marks these periods as inspected for future research.

[Web research and the Bitunix data audit](research/web/2026-10-10/README.md) document source provenance, execution/multiple-testing lessons and conflicting public five-minute candle responses. The new audit quarantines malformed or incomplete pages; no trading default changed. Some original papers and official documentation remain blocked pending the saved network-configuration review and publication.

The latest [six strategy follow-ups](research/STRATEGY_FOLLOWUP.md) test daily channels, trend-aligned RSI pullbacks, three recovery exits and an intermediate four-hour channel. None qualifies as a better replacement. The SMA5 exit increases winning-position counts and has positive total net in both reused accounts, but recent profit is only $265.41 versus the unchanged baseline's $3,955.55. Every failure, cost stress, trade log and fixed-horizon diagnostic is published; no new Pine recommendation follows from those results.

The new [NY first-retest research Pine](research/pine/NY_OR_Retest_Research.pine) is available for a separate native comparison on BTCUSDT15m. Its opening-range/cash-close design made+$1,375.94 on34 positions/18winners in2021–2022 and+$912.95 on46 positions/26winners in2024–September2026, after modeled costs/funding. Both cost stresses stay positive. It still fails the replacement gate: recent net is lower than Fibonacci v3 and only three recent half-year blocks are positive. It is visibly marked RESEARCH; the active baseline stays unchanged. [All five session designs, failures and port limitations](research/SESSION_STRATEGY_RESEARCH.md) are published.
