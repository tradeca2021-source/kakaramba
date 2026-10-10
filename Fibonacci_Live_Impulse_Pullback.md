# Fibonacci Live Impulse Pullback v2

Experimental redesign of the confirmed-endpoint strategy. Load `Fibonacci_Live_Impulse_Pullback.pine` on standard BTCUSDT 15-minute candles, with its default closed 4-hour trend filter. Keep the original strategy for comparison. The new script has not been compiled or backtested natively in TradingView here.

## Entry design

A closed candle breaks a previously confirmed structural pivot in the direction of the previous completed 4-hour EMA trend. The opposite confirmed pivot anchors the impulse. From the breakout onward, track the extreme of completed candles. On each subsequent candle, check the first 50% retracement against the extreme known at the preceding close. Freeze that extreme when the retracement occurs; the script does not wait for a new endpoint pivot to confirm.

A candle both extending that extreme and touching the retracement has unknown price ordering and consumes the setup. An impulse must span at least 2 ATR. The first 50–61.8% pullback must reject and reclaim the midpoint on its touch candle or the immediately following candle. Submit a stop entry one tick beyond the rejection candle; it can fill only on subsequent ticks. Stop stays beyond the pullback extreme with a 0.15 ATR buffer. Target stays at the frozen extreme.

The original cost-adjusted 1.5 net R entry gate, 0.25% risk, 95% equity notional cap, maximum 1 BTC, three-bar entry expiry and setup invalidations remain. No averaging or leverage. Optional filters and entry price protection remain off; research below uses those defaults. Model costs are 0.07% per side and two ticks of slippage. Pine excludes funding; research uses actual funding rates with candle-open notional as a price proxy.

## Known-period comparison

Checksum-verified Binance USD-M BTCUSDT 5m archives supply both execution candles and aggregated 15m signals. Seven separate $100,000 accounts cover 2024 H1/H2, 2025 H1/H2 and 2026 Q1/Q2/Q3. Summed profits are not a continuous portfolio return. These periods have already been examined and cannot serve as fresh validation.

| Design | Trades | Winners | Net USDT | Profit factor | Worst period 5m closing drawdown |
|---|---:|---:|---:|---:|---:|
| Confirmed endpoint control | 23 | 11 (47.8%) | 2,957.97 | 2.140 | 822.30 |
| Live endpoint 50% | 38 | 16 (42.1%) | 3,932.89 | 1.831 | 803.24 |
| Live endpoint 38.2% | 12 | 3 (25.0%) | -126.05 | 0.933 | 1,011.07 |
| Live endpoint 50%, 127.2% target | 125 | 30 (24.0%) | -1,935.73 | 0.905 | 3,900.63 |

The live-50 version has more profitable positions and greater aggregate net, but a lower win rate and profit factor. It loses in 2024 H1 and 2025 H2 and still takes zero trades in 2026 Q3. Much of its profit comes from 2024 H2. Higher fees (0.10% per side) reduce control/live-50 profits to $957.18/$1,501.54, with 16/28 trades because the cost-aware gate rejects additional setups. Increasing slippage to 20 ticks gives $2,520.89/$3,683.28 with 22/36 trades. Neither sensitivity check is independent validation.

This is a testable candidate, not a validated best strategy. Binance prices are a proxy for Bitunix. Five-minute candle paths remain unknown; the model prioritizes stops on ambiguous bracket touches and checks entry-subbar extremes conservatively. Fresh forward testing and native TradingView verification are required before a reliability claim.

## Reproduction

Run `python research/competition/live_impulse_study.py --output /tmp/fib-live-replay`. Cost sensitivity: `python research/competition/live_impulse_stress.py`. The predeclared protocol, full reports and individual trades are in `research/competition/live_impulse_protocol.json` and `research/results/competition/live_impulse_*.json` / `*_live_period*_trades.csv`. Execution tests include absence of future endpoint confirmation and rejection of ambiguous extension/touch candles; Pine checks cover actual predicates, costs, quantity and entry windows rather than native compilation.


## v2 execution diagnostics

Entry and exit rules retain the v1 defaults. The panel now records the last actual filled price, adverse ticks versus the submitted trigger, modeled reward ratio at that fill and modeled stopped risk as a percentage of equity frozen at submission. The ATR is also frozen at submission. This avoids silently substituting later volatility into the risk estimate. It handles positions that both open and close between chart calculations by reading the latest native closed-trade entry price and size before clearing the bracket.

Orange labels flag fills outside the bracket, below the intended reward floor or above the requested risk budget. These are observations after execution; they do not undo a fill, alter orders or guarantee realized losses. Funding is excluded, slippage is an assumed reserve, and price gaps can exceed modeled risk. A gap past the target is classified as invalid geometry instead of treating its absolute distance as positive reward.

The latest predeclared entry, protective-stop and timeframe comparisons are documented in [ENHANCEMENTS.md](research/results/competition/ENHANCEMENTS.md). None passed the criteria for adding a new trading mode. Retain the 15m chart, pivot5, prior closed4h EMA50, minimum netR1.5, fixed stop and swing target. The experimental strategy still needs unused-period and native TradingView verification.
