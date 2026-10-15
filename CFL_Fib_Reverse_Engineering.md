# Reverse-engineering _CFL_s_FibTrader from the supplied screenshots

Status: observed geometry reconstructed; full original engine not recovered. v99 is a study implementation on the existing BTC strategy, not a verified clone. The user confirmed matching the screenshot gold-23.6% target, replacing the old directional61.8% target.

## Verified level convention

Let O be the impulse origin, T its terminal extreme, and R=abs(T-O). The screenshots label origin100%, terminal0%. A label r denotes P(r)=T+r*(O-T).

- Entry50% = (O+T)/2.
- Gold-23.6% = T-0.236*(O-T), beyond terminal.
- Displayed61.8% = T+0.618*(O-T), a retracement into the impulse.
- Our former directional61.8% target = O+0.618*(T-O) = P(0.382). This differs from both the screenshot61.8% retracement and its gold extension.

Falling pictured leg: H7838.54,L7585.63,R252.91.50%=7712.085;38.2%=7682.24162;61.8%=7741.92838;gold-23.6%=7525.94324. Rounded labels match the screenshot7712.09,7682.24,7741.93,7525.94.

Rising pictured leg: H7847.56,Lapproximately7738.00,R109.56.50%=7792.78;38.2%=7805.70808;61.8%=7779.85192;gold-23.6%=7873.41616. These match the visible labels to image precision. A one-cent discrepancy in the midpoint read from the resized image cannot establish underlying full-precision anchors.

Before tick offsets, entry-to-target distance is0.736R instead of0.118R for our old target: approximately6.237 times as far. This is target distance, not reward/risk or a promised increase in profit factor. A farther target changes win rate, holding time and later order availability.

## Visible inputs and what they establish

| Input | Visible value | Interpretation / confidence |
|---|---:|---|
| TickSize |0.25|Explicit reference tick; instrument is not identified. BTC must use its own chart tick.|
| StartAnchor |7599.25|Explicit seed/reference price. How it enters the state machine is unknown.|
| TargetLossInTicks |200|Risk/sizing input by name; exact quantity formula unknown.|
| MaxSlFromEntryInTicks |150|Stop-distance constraint by name; exact stop reference and skip/clamp behavior unknown.|
| MinSlFromEntryInTicks |20|Same limitation.|
| NumTicksToFrontRun50 |2|Entry offset; likely buy above50%, sell below50%, consistent with earlier user explanation.|
| NumTicksToFrontRunPt |4|PT offset; likely long target below gold, short above gold.|
| MinMove |10|Minimum movement input; units, reference point and event timing unknown.|
| ExtensionLevel |-0.382|Separate from the gold-0.236 target; likely a series/extension threshold, not established as the order target.|
| ReversalLevel |0.236|Suggests fractional reversal recognition; wick/close, denominator and reset rules unknown.|
| FrontRunOfPt |2|Second distinct PT-related input; cannot determine its role or combine it with the4tick input.|
| StartDate |2025-04-04 ...|Date visible; full time/timezone cropped.|
| OnlyAllowTradesClearOfOpposing50 |True|Opposing midpoint matters. Exact meaning of clear is unknown.|

At0.25tick, entry offset2ticks=.50price units and target offset4ticks=1.00. Stop bounds20/150ticks mean5.00/37.50price units.200ticks means50price units BEFORE converting via contract point value, not necessarily50dollars. One possible quantity model is floor(200/stopDistanceTicks):40ticks risk gives5contracts, consistent with the shown5 but not sufficient to verify sizing.

## Unresolved engine behavior

The screen shows series that step and then hold, but it cannot establish the state transitions. StartAnchor, MinMove, ExtensionLevel and ReversalLevel suggest an anchored/recursive series engine may be involved. If these images share a0.25tick contract, fractional anchors ending.54/.63 are inconsistent with raw tradable extrema alone; alternatively the images may use a different/fractional feed. This is evidence to investigate, not proof of a particular anchor algorithm.

A red filled area is not sufficient evidence for the stop order price. The first trade image lacks a price axis and ratio labels, so its exact entry/target/stop ratios cannot be recovered numerically. The larger chart establishes the Fib level formulas; it does not prove which series generated the illustrated short trade. A bullish/bearish series may coexist with nested series; the number retained and expiry logic are unknown.

Exact replication needs original source, or a bar-by-bar recording showing anchors and values before/after extension and reversal events, plus full input descriptions and symbol/tick specifications. One static profitable trade cannot establish performance or the complete order logic.

## v99 study implementation

BTC_RBO_v99_Extension_Fib_Study.pine keeps the existing v98 confirmed-pivot anchors, ATR stop/quantity planning, SMC/local/larger confirmation, risk/fee/safety gates, finite lifetimes and clean display. It does NOT claim to reconstruct the unknown original series/stop/sizing code.

Implemented verified target convention: Target Fib Label defaults-0.236, with directional progress1.236 derived internally. Set label0.382 to recover the previous directional61.8% target. Entry front-run remains2 chart ticks; PT front-run now4. Actual orders round to the chart mintick and freeze after submission. Native chart tick is used;0.25 and7599.25 are not blindly applied to BTC.

Implemented explicit hypothesis for opposing50%: keep the latest confirmed midpoint for each direction, valid until its origin breaks or existing lifetime expires. Reject/cancel an unfilled order if the opposite midpoint lies anywhere in the inclusive entry-to-target interval. OnlyAllowTradesClearOfOpposing50 could mean something different in the original. Disable the new gate to isolate this assumption. Filled positions keep their stop/target.

No separate-.382 extension reset or0.236 reversal reset was invented. The original20–150tick stop bounds and200tick sizing budget are documented but not imposed on BTC.121 local source/formula/lifecycle checks passed, including labeled prices and mirrored long/short offsets. Native TradingView compilation, historical alignment and performance remain unverified. This file is a reviewable reconstruction study, not an exact or proven profitable replica.
