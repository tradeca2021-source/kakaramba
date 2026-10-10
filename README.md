# Fibonacci strategy: start here

The active experimental baseline is **[Fibonacci_Live_Impulse_Pullback.pine](Fibonacci_Live_Impulse_Pullback.pine)** (v3). Other Pine files are earlier designs or research artifacts. The Pivot3 Research candidate failed its chronological confirmation, is visibly marked REJECTED, and is archived in `research/rejected/`.

1. Load the active script on **standard BTCUSDT 15-minute candles**.
2. Select **Baseline BTC 15m (experimental)** in Settings → Inputs → Profile.
3. Check the banner: **pivot5 / trend240m EMA50 / impulse2ATR / filterNone**. The profile also fixes the modeled costs, minimum netR1.5 and 0.25% account risk. Custom setup/risk input values are ignored in baseline mode, including stale saved settings.

The profile requires a15m chart. To experiment with other settings, explicitly choose **Custom (unverified)**; the visible status changes accordingly. Date windows and chart display controls remain adjustable. Native strategy Properties are separate: the default0.07% commission and2tick slippage must match the modeled assumptions. Funding is excluded in Pine.

Rejection decision labels default off to reduce chart clutter; fill warnings stay on. Actual-fill diagnostics show whether execution consumed the intended reward margin or exceeded modeled risk. They observe fills and do not undo orders.

The strongest current known-period result is38 completed positions /16 winners /+$3,932.89 summed across seven independent account periods. Several periods lose and one has zero fills. This is repeatedly inspected Binance research data, not fresh validation or a verified Bitunix/TradingView result. Native Pine compilation has not been available in this environment.

See [strategy rules and limitations](Fibonacci_Live_Impulse_Pullback.md), [tuning results](research/results/competition/TUNING.md) and [enhancement comparisons](research/results/competition/ENHANCEMENTS.md). Full research protocols, trade-level outputs and execution tests are included in the repository.

Seventeen additional structural alternatives are recorded in [STRUCTURAL_RESEARCH.md](research/results/competition/STRUCTURAL_RESEARCH.md). None passed the declared qualification conditions, so no unproven trading default was promoted.
