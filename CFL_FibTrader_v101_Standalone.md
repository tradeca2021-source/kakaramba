# CFL v101 standalone screenshot reconstruction

This replaces the RBO-derived implementation for this reconstruction attempt. It does not replace other repository strategies or certify original-platform parity.

## What was wrong in v100

Changing target/stop ratios did not replace its confirmed-pivot RBO candidate selection, mandatory trend/SMC gates, volume filter, scheduled restrictions or30bar candidate lifecycle. Its clean mode hid the reference series and step zones. Consequently the new chart had a handful of isolated trades rather than the evolving series drawn in the supplied images. Those were architectural differences, not colors or rounding alone.

## v101 engine and display

File:CFL_FibTrader_v101_Standalone.pine. It derives from the repository's existing anchored v2 reconstruction in FibTrader_50to382_Confirmed_ZigZag.pine, not from v100/RBO. The original file is preserved. Other optional legacy engines are fixed inactive in this derivative; their code is not presented as original source.

A live series follows new extremes until a fractional retracement freezes it. A break beyond a frozen terminal creates a nested same-direction series and a same-origin continuation clone. Origin violation can create the opposite series; latest same-direction/same-origin series wins. The swing tracker uses minimum movement and fractional reversal. These are the repository's v2 HYPOTHESES, not rules verified from the missing CFL source.

Drawings are generated from that series state: stepped shaded50–61.8% regions, price levels and separate gold-23.6% context extensions. The current working trade target remains38.2%, protective stop61.8% plus one tick, entry50% with2tick front-run, PT4tick front-run. Gold extension context and trade target are separate. Draw only the newest3 series plus quoted/open series by default; keep only100 series in the model. Use its drawing options if the chart needs more or fewer zones.

No RBO/SMC/local-or-larger trend gate, VWAP/volume confirmation, Sunday/news/session gate, reward/risk minimum, daily liquidation or discretionary trailing exit is active. There is no external library import and no HTF security request. Both directions are considered from live series. Each active trade gets its quote's fixed protective bracket; a one-fill OCA group prevents simultaneous opposite-entry fills. Position cap1 is a reconstruction constraint, not established original stacking behavior.

## Defaults and comparisons

StartAnchor0 means initialize from the first eligible bar; it is not the pictured7599.25 unless entered. The inherited StartDate2025-04-0410:00 is a configurable working value; the pictured time is cropped, so it is not verified. Starting history/anchor/timezone/data feed affect later nested series. Fib engine timeframe defaults to chart timeframe; optional aggregation is manual from completed chart bars.

Native chart TickSize is used by default. Auto-scale is ON for the user's BTC chart: reference price7730, price multiplier close/7730, tick-distance multiplier priceMultiplier*0.25/chartTick. This changes MinMove, stop limits, freeze distance and modeled risk-tick budget. It is explicitly a BTC adaptation, not literal matching of the source instrument. For reference-instrument comparisons turn auto-scale OFF and enter the matching tick,7599.25 anchor and exact start date/history. Do not apply a7599 seed blindly to BTC near80000.

Source-like quantity hypothesis: floor(TargetLossInTicks*effectiveScale/stopTicks), minimum1 integer unit. TargetLoss default200; MinSl20; MaxSl150; MinMove10; reversal0.236; extension-0.382. Freeze-point threshold20 is an additional reconstruction assumption. Integer source-contract sizing and zero-margin futures-style simulation are inherited for reference experiments; this is not the v98 equity-percent BTC risk model. Strategy cost defaults are0.06% per side and2tick slippage for BTC, not recovered source costs. Review symbol contract units and Properties before using results.

Execution is bar-close. Historical OHLC path assumes low→high on an up candle and high→low on a down candle. It cannot recover actual tick order or original order-update timing. New limits cannot backfill an earlier touch. Only a native replay with matching source data can establish execution parity.

## Validation and unresolved parity

25 local source/formula/state-transition checks passed. They verify the selected reconstruction model and quote math, not the original executable. The complete file passed pynescript0.3.0 parsing without diagnostics; the file/AST hashes are recorded in CFL_FibTrader_v101_Standalone.verification.json. This third-party parser is not a TradingView compiler. No native compilation, same-series screenshot alignment or profitability has been established.

Use this file IN PLACE OF the visible RBO instance. No amount of simultaneous overlaying makes v100 equivalent. Keep a comparable view around one same-series trade with price scale and times for the next mismatch assessment. This implementation addresses the architectural mismatch; it is not a100% claim.
