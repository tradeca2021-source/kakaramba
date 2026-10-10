# Channel trend follower: stronger development, failed historical test

This is a built and tested Python research strategy, not a promoted Pine replacement. The candidate passed development and failed the separately frozen historical test. The unchanged Fibonacci control also lost in that test; neither has demonstrated a dependable edge across these histories.

## Fixed design

- Use standard 15m candles for decisions and five-minute candles for execution.
- At a completed four-hour close above the preceding 20 four-hour highs, buy at the next five-minute open. Below the preceding 20 lows, sell short.
- Place a protective stop two four-hour ATR(14) away from the signal close. Size with 0.25% equity risk including modeled costs and gap allowance; preserve 95% exposure and maximum 1 BTC.
- At each later completed four-hour close, tighten the stop toward the last ten completed four-hour lows for a long, or highs for a short, one tick outside the channel. Never loosen it.
- No preset profit target, partial exits, pyramiding, trend filter or parameter search. A trade can remain open across many signal periods. Model gaps, fees and funding rather than assuming the initial risk budget guarantees the realized loss.

See [channel_engine.py](../../competition/channel_engine.py) and [the predeclared protocol](../../competition/channel_protocol.json). A fixed reward/risk gate cannot apply to an uncapped trend exit; qualification depends on realized net results. This is an explicit change from the failed regime architecture, not a claim of guaranteed reward.

## Same-account comparisons

Each evaluation starts with $100,000 and runs continuously without resets at half-year boundaries. The two histories are separate accounts; their nets are not a combined continuous portfolio return.

| Period / strategy | Positions | Winners | Net USDT | Net PF | Largest 5m closing drawdown, USDT |
|---|---:|---:|---:|---:|---:|
| Development 2024–September 2026 / Fibonacci baseline | 38 | 16 | +3,955.55 | 1.831 | 1,109.98 |
| Development / channel | 195 | 65 | +7,649.64 | 1.378 | 3,165.15 |
| Reserved older history 2021–2022 / Fibonacci baseline | 31 | 8 | -737.26 | 0.832 | 1,702.82 |
| Reserved older history / channel | 147 | 51 | -2,583.90 | 0.828 | 3,494.85 |

The development channel win rate is 33.3%, versus 42.1% for the baseline. It has more winning positions and more net profit, but a lower profit factor and a higher drawdown. Its five-minute closing peak drawdown is about 2.97% in development and 3.47% in older history; true intrabar and native drawdowns can be larger.

The candidate passed all declared development conditions: at least 100 positions, greater net than the baseline, at least four positive half-year blocks, positive net after removing its best trade and drawdown below 5%. Five of six development blocks were positive. The best trade contributed $3,362.58 of its $7,649.64 net, leaving $4,287.06 without that trade.

Candidate source and selection were frozen in commit `95df807` before loading the reserved archives. The older test lost in three of four half-year blocks and failed positive net, positive net without the best trade, PF at least 1.20 and three positive half-years. The channel also lost $3,010.47 under 0.10% per-side fees and $2,659.68 under 20-tick slippage. The historical qualification is **false**. It was not retuned after that result and was not ported to Pine.

Seven-day block resampling of marked daily returns produces intervals crossing zero for both the channel development result (-3.45% to +20.78%) and historical result (-8.37% to +3.77%). These are exploratory uncertainty estimates, not evidence that the development result will persist.

## Evidence and limitations

[development.json](development.json), [frozen_selection.json](frozen_selection.json) and [historical.json](historical.json) publish all gates, source hashes, archive hashes, confidence intervals and complete candidate/control cost-stress comparisons. CSV files contain full closed-position logs, actual research funding cashflows and marked daily continuous equity. Funding uses each five-minute opening price as a notional proxy, not the exact exchange mark price.

The historical load verified 108 official monthly SHA256 archives for 2020 warm-up and 2021–2022 evaluation. No 15m/5m OHLC discrepancies occurred in that load. The development load retains the three previously documented discrepancies and uses canonical five-minute aggregation. Research candles are Binance USD-M BTCUSDT, not Bitunix. Native TradingView compilation and venue execution were not available.

The historical data are older than development: this tests transfer to older market regimes, not forward performance. They were unopened for this candidate at selection, but are now inspected and must not be called fresh validation for future designs. See [DATA_ACCESS_LEDGER.md](../../DATA_ACCESS_LEDGER.md).

Reproduce the known development results with `python research/competition/reproduce_strategy_studies.py channel --output /tmp/channel-audit`. This checks frozen sources, archive manifests and exact report/CSV matches without another selection. The research-selection drivers intentionally reject a new untouched-data claim when reserved archives already exist. Frozen historical results can be reproduced using `python research/competition/channel_study.py historical --output <directory-containing-unchanged-frozen-files>` with identical source hashes and copied development/selection files. The resulting repeat is reproduction, not another independent test.

No new strategy is promoted. The existing Pine baseline stays available as an experimental reference; its own historical loss must accompany any description of its earlier positive results.
