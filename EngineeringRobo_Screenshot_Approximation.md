# EngineeringRobo screenshot approximation

Independent Pine v6 reconstruction of visible controls and visual elements. This is not the original indicator, an AI model, or a verified reproduction of its trades. Paste the `.pine` file into TradingView Pine Editor and add it to a standard candle chart, initially 15 minutes.

## Controls and inferred behavior

| Screenshot control | This implementation |
| --- | --- |
| AI POWER, main checkbox | Supertrend multiplier (ATR length 10); confirmed reversals produce signals; checkbox gates outputs |
| CHANGE CANDLE COLOR | Green/red by Supertrend direction |
| SUPER SIGNAL BOOSTER | Confirmed pivots with RSI below 45 / above 55 at the pivot; signals appear at detection |
| HODL LINE | Supertrend trailing line |
| BULL | Green background above EMA200 |
| BUY WITH GREEN CLOUD / SELL WITH RED CLOUD | EMA20–EMA50 fill |
| AI TAKE PROFIT SIGNAL | Once per signal, close reaches two signal-time ATRs favorably; visual marker only |
| EARLY BIRD | Close crosses EMA20 against the current Supertrend regime |
| DASHBOARD, location, size, symbols | Configurable table with four markets |
| Multi-timeframe | Selected timeframe trend row; Chart uses chart timeframe |
| AI Social Intelligence Score | Optional N/A field: no social feed or identifiable formula |
| BEST BUY - BEST SELL LEVELS | Previous rolling high/low; no claim of optimal entries |
| MA, MA | Independently selectable SMA/EMA/WMA/RMA and lengths |
| EMA Trend Lines | EMA20/50/100/200 |
| Support/resistance, Channel | Latest confirmed pivot high/low |
| Periods | Previous rolling high/low, separate enable switch |
| Levels | Bounded collection of confirmed pivot levels, separate enable switch |
| Trendlines, left/right, dashed history | Connect pivot values at their detection bars; optionally retain up to 40 prior lines as dashed |
| Simulation | Illustrative last signal-entry plot; no simulated orders, fills, equity, or performance |

Extra fixed-price inputs were removed to match the reference input layout. The indicator title matches the reference; this remains an independent approximation, as documented here and in the source header.

The dashboard uses previous source bars: SMA trend, ATR volatility, volume versus 96-bar SMA, RSI, and MFI as a money-flow proxy. Correlation uses price changes versus the selected BTC reference over 30 chart samples. It is not a claim to match the original dashboard. Nonmatching trading sessions and missing data affect comparisons. Timeframes below the chart timeframe display N/A to avoid misleading intrabar sampling; use the 15-minute chart for the depicted layout. Closed higher-timeframe readings intentionally lag developing candles.

TradingView generates the Style and Visibility tabs. Named plots expose their styling there; visibility ranges are native chart settings. No custom recreation of those platform tabs is necessary.

## Validation

Source reviewed for input wiring, bounded line retention, plot/request budgets, and signal-time ATR handling. No native Pine compiler is available in this environment, so compilation and chart behavior still require verification in TradingView. Local Python strategy tests do not validate this indicator and are not presented as evidence for it.

## Reference Style tab

Plot declarations now follow the supplied Style screenshot order: Plot; Shapes ×3; Plot ×2; AI Take Profit; Shapes ×2; Early Bird; Shapes ×4; AI Colors; Smart Money IN; Smart Money OUT; Overbought; Oversold; MA №1; MA №2; EMA20/50/100/200; Plots Background ×4. Shapes use the reference label/triangle/cross types and default colors. Pine and TradingView generate the remaining object, precision, scale, and visibility controls.

These names match the reference UI and do not establish the original formulas. In particular, Smart Money IN/OUT draw the reconstructed pivot levels colored by MFI, and Overbought/Oversold draw rolling price levels colored by RSI. They are price-scale overlays rather than raw oscillator plots. Simulation uses a line drawing to avoid adding an extra Style row. Exact rendering and generated color-picker order need native TradingView verification; screenshots alone do not validate them.


## Signal visibility correction

Main signals remain confirmed Supertrend reversals; that engine was not replaced without evidence that its formula failed. Main and boost labels now use small rather than tiny text, duplicate blank reversal markers are limited to optional BULL mode, and plots plus the dashboard explicitly target the candle pane with `force_overlay`. Boost exhaustion uses RSI on the pivot bar, with the actual signal still emitted on its later confirmation bar. Dashboard counts show cumulative confirmed main buy/sell signals across loaded history, not only the visible window. These changes do not manufacture entries in a window with no qualifying reversal.

After replacing the source in TradingView, remove the prior indicator instance and add a fresh instance so saved Style overrides cannot hide the new markers. Leave the main checkbox, SUPER SIGNAL BOOSTER, and DASHBOARD enabled. Alerts need to be recreated after script updates to use the revised logic. Native compilation and on-chart verification remain outstanding; the screenshot alone does not establish why every plot/table was hidden.


## Follow-up review

Each dashboard column now has a separate written function call for rolling correlation history. Completed-bar metric requests use consistent lookahead with an explicit one-bar offset. Missing volume, incomplete trend warm-up, invalid symbols, and lower-than-chart trend timeframes display N/A rather than a fabricated LOW/BEARISH reading. Explicit 1000-bar history allocation covers configurable pivots and RSI offsets. Added the existing profit-distance event as an alert condition. These are source-level corrections; native Pine compilation and TradingView execution remain unverified.

Reload checklist: replace all editor contents, Save, remove old chart instances, Add to chart, and ensure the main checkbox, DASHBOARD, and SUPER SIGNAL BOOSTER remain enabled. Reset Style defaults if saved overrides remain. In the dashboard, B/S counts apply to the full loaded history: nonzero counts with absent visible labels can mean the events are outside the visible window or hidden by chart settings. A zero count is not permission to invent trades. Native comparison requires the chart symbol, timeframe, date window and settings; the original BTC example and a different instrument cannot be expected to have identical signals.


## Native user-chart evidence

The user supplied a screenshot of Signal Check v2 on BTC with the orange trailing line and BUY/SELL markers visible. This confirms rendering of the isolated Supertrend reversal path on that chart; it does not validate the full indicator or dashboard. Doubled markers in that screenshot were deliberately created by the diagnostic's parallel plotshape and label.new outputs. EngineeringRobo_Signals.pine removes the duplicate drawing path and diagnostic counters; the same confirmed-reversal conditions now drive one marker per event. Its HODL line is optional and disabled by default. This signal-only file is independent of dashboard requests and retains separate BUY/SELL alerts. It is not the full screenshot reconstruction.
