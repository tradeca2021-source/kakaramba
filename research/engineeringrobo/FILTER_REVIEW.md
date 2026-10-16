# Entry context filter investigation — 15 October 2026

**No filter qualified.** Excluding apparent range extremes did not reliably distinguish losing from winning entries. The strongest remaining issue is negative expectancy after costs, not simply missing a trend or overbought/oversold checkbox. The unchanged main signal is the reconstructed Supertrend, not independently recovered proprietary EngineeringRobo logic.

This follow-up was designed after inspecting the earlier failed exit study. The complete bounded filter definitions are in `filter_protocol.json`. All periods are previously inspected Binance BTCUSDT perpetual history; they are exploratory, not untouched validation or actual Bitunix performance.

## Method

Thirteen configurations: unfiltered control plus twelve entry filters/combinations. Every variant retains the same 1.5 ATR stop, 2 ATR target, closed-bar Supertrend 2.5/10 and frozen ATR14. Context uses only information available at the signal close. Entries fill next open with adverse slippage. Filtered opposite signals still close the old position; rejected entries stay flat. Range extremes exclude the signal candle itself. Room-to-extreme and fee gates are checked again against the next opening fill. Four-hour trend uses only completed UTC bars; no developing HTF candle or retrospectively known pivot is allowed.

Primary size is **0.1 BTC**, with independent $100,000 accounts per split, to compare entry quality without most of the original 1 BTC buying-power rejections. Base fees are 0.07% per side, tick0.1, two ticks slippage and supplied historical funding using a last-price proxy. The JSON also retains the original 1 BTC sizing comparison, 0.1% fee stress and20tick slippage stress. Costs and sizing differ from a frictionless signal-label comparison.

| Filter | Jan–Jun net | Jul–Aug net | September net | September trades | September PF |
|---|---:|---:|---:|---:|---:|
| unfiltered | $-7,266.46 | $-2,191.32 | $-416.11 | 90 | 0.759 |
| range_avoid_24h | $-5,641.64 | $-1,735.84 | $-430.65 | 69 | 0.687 |
| range_avoid_7d | $-6,495.33 | $-1,353.24 | $-521.93 | 74 | 0.652 |
| room_24h | $-5,278.56 | $-1,712.11 | $-432.22 | 64 | 0.667 |
| room_7d | $-7,065.25 | $-2,122.00 | $-499.75 | 86 | 0.701 |
| trend_ema200 | $-3,226.90 | $-1,003.53 | $-193.96 | 36 | 0.723 |
| trend_4h_ema50 | $-3,007.62 | $-1,116.08 | $-286.51 | 37 | 0.603 |
| adx20 | $-4,066.49 | $-1,635.38 | $-292.74 | 45 | 0.719 |
| rsi_not_extended | $-6,130.78 | $-1,801.92 | $-496.16 | 79 | 0.681 |
| atr_covers_fees | $-5,584.62 | $-1,293.88 | $55.21 | 60 | 1.048 |
| range_and_trend | $-1,728.04 | $-631.49 | $-226.13 | 17 | 0.388 |
| room_and_trend | $-1,434.41 | $-591.67 | $-125.99 | 14 | 0.532 |
| breakout_24h | $-554.07 | $-33.63 | $94.44 | 5 | 3.158 |

## What the results say

- **Avoiding longs near highs / shorts near lows:** The24h filter rejects longs above80% and shorts below20% of the preceding range, including breakouts. September net worsened from −$416 to −$431. The rejected baseline trades made +$14.54 overall, while retained trades lost $430.65. In July–August, retained trades averaged −$11.42 versus −$10.59 for rejected trades. The simple location rule did not isolate the bad trades. Seven-day context also failed.
- **Room to support/resistance:** Requiring at least2ATR room to the preceding24h extreme reduced trades but September net worsened to −$432. This uses historical range boundaries as objective support/resistance proxies; it does not test every discretionary level or order-book definition. No screenshot fixed BTC levels were used.
- **Trend alignment:** EMA200 and completed4h EMA50 filters reduced total loss mainly by trading less. For EMA200, development mean loss was $14.41 per executed trade versus $13.58 unfiltered; July–August was $13.38 versus $11.24. Lower total loss alone is not improved expectancy.
- **ADX/RSI:** ADX>=20 and excluding RSI extensions did not establish positive expectancy. Combining location/room with trend did not fix this.
- **Volatility versus cost:** Requiring the2ATR gross target to exceed3times modeled round-trip friction produced +$55.21 in September, PF1.05, but lost $5,584.62 in development and $1,293.88 in July–August. September fell to −$97.37 at higher fees. Cost stress can change the set of eligible trades because this is an economic entry gate; it is not a fixed-trade sensitivity table. This is a useful safeguard hypothesis, not a validated profitable strategy.
- **Breakout counter-test:** Only5September trades produced +$94.43; January–June and July–August lost, with only20 and6trades. The later small positive sample cannot justify promotion. Breakouts demonstrate why “high price means avoid longs” is not a universal rule.

## What may actually be missing

1. **Signal identity and timing.** This code trades Supertrend flips. Blue Super Boost markers are separate confirmed-pivot/RSI annotations, not entries. The original proprietary indicator logic has not been recovered from screenshots. A chart that appears to catch every turn cannot substitute for executable, timestamped signals.
2. **An entry with positive expectancy.** In development, the unfiltered0.1BTC control lost $7,266.46 including $5,571.65 commissions. Its trade gross PnL excluding commissions/funding was already −$1,695.38 (slippage remains included). Fees are substantial but not the only failure. September gross was positive but fees consumed it.
3. **Different treatment of trends and ranges.** A long near a high can be a valid breakout; a short near a low can be continuation. A future design should explicitly distinguish a breakout from a failed breakout/retest, rather than universally blocking extremes. That requires a new, narrowly defined trigger and reserved forward evaluation, not another search over this known history.
4. **Native fill parity and venue costs.** Compare matched TradingView exported trades and actual venue candles/funding before interpreting small differences as edge. There is no native Pine parity claim.

## Decision

Do not add these filters to the live/default Pine strategy as improvements. Keep them in the research harness. A sensible next experiment is one fixed breakout/retest trigger with a time-limited entry and objective invalidation, alongside the original control, at actual account fees. Freeze it before collecting a new forward sample. Structure-based stops, retest entries, session filters and alternative signal sources were not tested by this entry-filter study; none is claimed profitable.

## Verification and artifacts

219 unit tests pass, including prior-range exclusion/window expiry, prefix causality, completed4h timing, rejected-opposite exits and opening-gap economic checks. Tests establish mechanics, not profits. SHA256 archive/source/protocol hashes, all156 period/size/cost summaries and accepted/rejected baseline diagnostics are in `filter_results/report.json`. Base trade ledgers and all signal contexts are retained alongside it.

Reproduce from repository root: `python3 -B research/engineeringrobo/filter_study.py`. Full local run: `/workspace/engineeringrobo-filter-results/20261015T141830866315Z`. Funding mark approximation, stop-first5m ties, sampled drawdown and conservative margin treatment are inherited from the original replay. All results are exploratory proxy evidence.
