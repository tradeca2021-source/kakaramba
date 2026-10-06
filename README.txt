BTC RBO v74 conversion

Paste the entire BTC_RBO_v74_Fib.pine file into TradingView Pine Editor. Use a linear BTCUSDT/BTCUSD perpetual chart whose strategy quantity is in BTC. Inverse and exchange contract-unit markets require separate sizing conversion.

Defaults: 24-hour permitted session, all seven weekdays enabled, blocked intraday sessions off, EOD liquidation off, New York midnight risk-day reset, 0.001 BTC quantity step, 1 BTC max/fixed size, 1x margin, 0.06% commission per fill, two chart ticks slippage. News filters and original FVG/Fibonacci/ORB/risk logic are retained. NY and London ORBs remain time-based signals. Daily VWAP follows the chart daily anchor.

Set the quantity step and commission for your exchange. Set Webhook Market Symbol to the exact identifier your execution service accepts; verify it supports your perpetual exchange and BTC-unit quantities. The original TradersPost payload structure remains. Funding fees are not modeled.

External dependency: access to traderjoeb/PropFirm_News_Dates/6 is required. Publishing a copy under a different profile requires changing the import path.

Local static checks and 56 partial-allocation cases passed. TradingView compilation, backtesting, and broker webhook execution have not been performed here.
