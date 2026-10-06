RBO v75: cost-aware linear crypto perpetual strategy

BTC_RBO_v74_Fib.pine retains its filename for compatibility; its strategy title is now v75. Paste the entire file into TradingView Pine Editor. Use a linear BTCUSDT/ETHUSDT perpetual chart whose strategy quantity is in the base coin. Inverse contracts and markets sized in exchange contract units require separate sizing conversion.

Changes from v74:
- Entry cost filter covers all six entry paths. The first planned target must cover at least 1.5 times estimated round-trip fees/slippage. Bar-by-bar mode uses its TP1 activation distance. Disable the filter to compare baseline behavior.
- Dynamic sizing includes estimated execution costs within the existing risk budget. Fixed sizing retains its quantity cap.
- Break-even prices cover estimated round-trip costs when a break-even mode is enabled; the original mode remains off by default. Both directions round outward to chart ticks.
- Empty Webhook Market Symbol Override uses chart base + quote currency, avoiding BTC orders from an ETH chart. Configure an override for execution services using different identifiers. Verify perpetual support and quantity units.
- Replacement-stop alerts preserve actual fractional remaining quantity.

Estimated Fee Per Side (0.06%) and Estimated Slippage Per Side (2 ticks) must match Strategy Properties. Pine cannot read those Properties values. Estimates exclude funding, spread and actual fill variation. Entry checks use current ATR; exit distances use ATR at fill. A planned target passing the filter does not ensure a profitable trade, especially on early stops or reversal exits.

Defaults retained: all seven days, 24-hour allowed session, blocked intraday windows off, EOD liquidation off, New York midnight risk-day reset, 0.001 base-coin step, 1 base coin maximum/fixed size, 1x margin. Set step and size for the selected market. News filters and original FVG/Fibonacci/ORB logic remain. NY and London ORBs remain time-based signals; daily VWAP follows the chart anchor.

External dependency: access to traderjoeb/PropFirm_News_Dates/6 is required. A copy published under another profile requires updating the import path.

Validation: static coverage of all six entry paths; mathematical checks that cost-adjusted BTC/ETH break-even prices cover modeled fees/slippage and dynamic sizing stays within the modeled risk budget; git diff whitespace check. TradingView compilation, new backtests and broker webhook execution have not been performed. No improved return is claimed.

Current default candidate for BTCUSDT perpetual, 1-minute: minimum target/cost ratio 2.0, ADX 25, minimum FVG score 55, minimum Fib Action score 55, risk 0.15%, score-based risk scaling off, wick-based hard stops. These are recommended trial defaults, not a backtest-verified optimum. ATR targets, trailing settings and enabled trading days are retained. Existing TradingView strategy instances may retain previous input values: reset settings or add a fresh instance to use these defaults.
