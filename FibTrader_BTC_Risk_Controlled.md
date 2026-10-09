# BTC Zig Zag risk-controlled variant

Use `FibTrader_BTC_ZigZag_Risk_Controlled.pine` as a new TradingView script. Keep the existing `FibTrader_50to382_Confirmed_ZigZag.pine` for comparison. The news library `tradeca2021/PropFirm_News_Dates/6` remains required.

The setup remains a confirmed swing followed by a rejection candle at its exact 50% retracement. Short: touch 50%, bearish body, close below it. Long: mirrored. The rejection must follow swing confirmation. Market entries execute on the next available tick, not retrospectively at 50%.

## Changes and defaults

- Calculate on bar close, with 100% margin (1x leverage), percentage commission of 0.06% per side and two ticks of slippage. These are illustrative costs; use the actual exchange rates.
- Risk 0.15% of current equity per entry, including estimated entry/stop fees, two-sided slippage and an extra 0.25 ATR stop-gap sizing allowance.
- Round quantity down to a 0.001 BTC step, require at least 0.001 BTC, and cap quantity at 1 BTC and notional at 100% of equity. Skip undersized trades; never force one BTC. Fixed-size mode remains bounded by these risk and exposure limits.
- Always require estimated net proceeds at the original Fib target to be positive. The optional minimum net reward/risk floor defaults to zero. Costs and risk controls apply in MultiCharts mode too.
- Default to one trade per swing; stop considering a Zig Zag setup after 48 chart bars. One open position is permitted.
- Cancel entries and close positions when realized plus open equity PnL since the exchange-calendar day began loses 1% of starting-day equity. This check runs at bar close; gaps and intrabar losses can exceed the limit.
- Stronger rejection-close and EMA trend filters are optional and OFF by default. They are unoptimized comparison settings.

The existing 38.2% target reference, 61.8% stop and selected exit controller are retained. The default exit mode is still bar-by-bar trailing: reaching the target activates trailing rather than guarantees a fixed take-profit. A positive modeled target is not a forecast of realized trailing returns. Failure signals are observation-only in this version.

Modeled fee/slippage inputs and Strategy Properties must match. Funding, spread and unexpected gaps are not modeled. Quantity is sized before the next-tick market fill, so a gap can exceed the modeled risk or exposure. The gap allowance does not move the stop or guarantee a maximum loss. BTC quantity defaults are not futures contract settings.

## Validation and comparison

Run `python3 tests/test_fibtrader_btc_risk.py` from the repository root. It evaluates the actual Pine sizing/economic expressions and checks risk/exposure bounds and preservation of swing/exit code. It is not a native Pine compiler or market simulator.

Native Pine compilation and performance of this new version are unverified. The previously uploaded BTC 15-minute export belongs to the earlier script and does not validate this variant.

1. Add a fresh instance and verify the inputs and Strategy Properties, including the chart's normal candle type, timeframe, bar magnifier, margin, commission and slippage.
2. Rerun the old version with the same actual costs and margin, then compare this variant on the same history.
3. Hold signal/exit settings constant before testing optional filters one at a time. Check separate periods, long/short results, trade counts, net profit, drawdown and results excluding the largest winner.
4. Export the new Properties and Trades sheets. Confirm that quantity, notional and realized costs match the exchange constraints. Use replay/chart data to inspect rejection candles; a trade export alone cannot reveal all missed signals.

No increase in profitability is claimed without those runs.
