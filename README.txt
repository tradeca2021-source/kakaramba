RBO v77: blind 50% Fibonacci entries / directional 61.8% profit target

Compiler-size refactor: large blind-order, legacy entry/exit and drawing/dashboard blocks now run through helpers at their original execution points. Mutable scalar and drawing-handle state is returned explicitly to global callers. All three execution modes, defaults, order formulas and global plots are retained. Approximately 392 original main-body source lines moved into nine helpers; approximate non-comment main-body lines decreased from 2485 to 2190. Static body-equivalence, default/plot comparisons and whitespace checks passed, with an independent agent review. TradingView compilation is still required to confirm the reported main-body limit is resolved; no Pine compiler is available locally. Recompile and verify trades in each selected execution mode before creating new alerts. No profitability change is claimed.

Default mode: Blind 50% Limit / Fib Target. BTC_RBO_v74_Fib.pine retains its filename. v76 qualified FVG 50/61.8 and legacy multi-target modes remain selectable.

Confirmed swing high/low pairs on the chart timeframe define an impulse. The default pivot strength is three bars on each side, configurable. An upward pair runs from a confirmed low to a later confirmed high; a downward pair from a confirmed high to a later confirmed low. Pivots become known only after the right-side bars close. Limits are submitted then, never backdated to pivot bars. Already-crossed midpoint entries are skipped. Simultaneous high/low pivots do not create a new ordered impulse. Rolling-lookback extrema remain an optional anchor method.

Blind entry means no FVG, candle reaction, ORB, ADX, relative-volume or HTF trend entry requirement. Fib direction selects long or short; both are eligible regardless of HTF trend. Optional VWAP alignment is off by default. Schedule/news, daily limits, position sizing and estimated-cost safeguards remain configurable and active according to existing settings. Opposite-FVG cancellation and emergency exits do not apply to blind mode.

The midpoint entry is front-run by two chart ticks by default: long = midpoint + ticks; short = midpoint - ticks. The requested gold profit target is directional 61.8% progress: long = low + range x 0.618; short = high - range x 0.618. Exit is also front-run by two ticks: long target minus ticks; short target plus ticks. Both offsets and target ratio are configurable. For anchors 100/200 and tick 0.1, defaults give long entry 150.2 / target 161.6 and short entry 149.8 / target 138.4. This is not the retracement 61.8% line on the entry side.

A setup freezes entry, target, stop and base-coin quantity. The default stop preserves v76 ATR-from-entry placement; a configurable alternative places it beyond the impulse origin plus a tick buffer. The screenshot did not specify a stop rule. ATR is sampled when arming. The existing hard-loss cap may tighten either stop. Actual reward after front-running must remain at least one tick and pass the optional target/cost filter. Risk sizing includes estimated costs when enabled; score-based FVG risk scaling is not used in blind mode.

One pending or open series is managed at a time; simultaneous nested series are not implemented. One impulse anchor pair receives one attempt. A rejected, canceled or completed impulse never re-arms merely because price touches again. New pairs can arm while flat. Pending entries and brackets cancel together on timeout(default 30 bars), stop invalidation or schedule/news/daily/VWAP veto. Open trades retain fixed bracket protection. A full-position stop/target bracket is submitted with the entry; no reaction delay, partial exits, break-even or trailing changes in blind mode. Same-bar entry/exit completion is detected via closed-trade count.

Clean-chart mode(default on) hides legacy ORB/daily/HTF/debug-FVG/ESL drawings. Actual entry remains orange, profit target gold and stop magenta. The independent VWAP visibility input remains available. This reproduces the requested trading rules; exact series/drawings from a third-party indicator cannot be recovered solely from the screenshot.

TradingView strategy limits are broker-emulator orders. Existing webhook messages are order-fill alerts, so they do not place an exchange-resting limit when the setup first arms. The existing optional broker ESL is a separate failsafe; TP/SL messages depend on TradingView fills and your webhook service. This update does not add a native exchange bracket or order-flow data.

Reset inputs or add a fresh strategy instance after updating; recreate alerts. Static/mathematical checks cannot compile Pine. TradingView compilation, BTC backtests, Bar Magnifier lifecycle checks, real-time fills and webhook execution remain unverified. No profitability improvement is claimed.

Previous mode notes:

RBO v76: Fib 50% limit entry / directional 61.8% target

The default Fibonacci Execution Mode is now "50% Entry / 61.8% Target". BTC_RBO_v74_Fib.pine retains its filename. "Legacy FVG Entries / Multi-Target" preserves the prior entry/exit engine; impulse direction ordering is corrected in both modes (Pine highestbars/lowestbars offsets are signed).

New mode uses confirmed bars and qualified FVG/ORB/swing/sweep setups, with the existing schedule/news, VWAP, ADX, exhaustion, ORB-extension, directional-quality and cost guards. It is not an unconditional order at every Fib touch. It requires a bullish impulse for longs or bearish impulse for shorts and places a resting limit only while close remains above the long entry / below the short entry. Late setups already through 50% are skipped. Limits may fill at a better price on gaps; exact fills are not guaranteed.

Levels use directional progress through the snapshotted impulse. For low=100 and high=200: long limit=150 and target=161.8; short limit=150 and target=138.2. This 61.8% progress target is on the profitable side of 50%; it is distinct from the prior retracement line labelled 61.8%. New chart lines show frozen entry, target and stop for the actual order instead of the moving retracement plots.

Entry, target, stop and quantity are frozen when submitted. The stop is entry +/- setup ATR x ATR Stop Multiplier, rounded outward, tightened by the existing enabled per-trade hard-loss cap, and always a wick stop. Legacy stop type/behavior inputs apply only in Legacy mode. Risk sizing includes estimated fees/slippage when enabled, quantity step, maximum size and available 1x equity. The cost filter checks the actual 50% to 61.8% reward distance, rather than the legacy ATR TP1 estimate.

A full-position stop/61.8% bracket is submitted in the same calculation as the entry and maintained unchanged, bypassing the live exit-placement delay. New mode uses one position and one full exit; legacy partial TP1/TP2, break-even and trailing settings do not apply. Existing daily/session/FOMC and opposing-FVG safety exits remain; the optional per-trade profit cap is a market safety exit on strategy calculations, normally bar close, and may exit before 61.8%. Pending orders and their bracket are canceled together on timeout, invalidation or filter/session veto while flat; an open trade keeps its protection. Same-bar entry/exit completion is detected through closed-trade count.

Webhook entry messages still place the existing optional fixed broker ESL hard-loss failsafe. It is not the simulated ATR stop or a native broker take-profit bracket. Fib TP/SL exits are delivered by TradingView order-fill alerts; actual broker execution depends on the webhook service. No partial-exit BE stop replacements are used in this mode.

Static and mathematical checks do not compile Pine. TradingView compilation, long/short order lifecycle with Bar Magnifier (including same-bar fills, gap fills and canceled pending orders), real-time protective-order behavior, webhook execution and BTC backtests remain required. No profitability improvement is established. Reset existing inputs or add a fresh strategy instance, and recreate alerts after updating.

Prior v75 notes (legacy mode):

RBO v75: cost-aware linear crypto perpetual strategy

BTC_RBO_v74_Fib.pine retains its filename for compatibility; its strategy title is now v75. Paste the entire file into TradingView Pine Editor. Use a linear BTCUSDT/ETHUSDT perpetual chart whose strategy quantity is in the base coin. Inverse contracts and markets sized in exchange contract units require separate sizing conversion.

Changes from v74:
- Entry cost filter covers all six entry paths. The first planned target must cover at least 2.0 times estimated round-trip fees/slippage. Bar-by-bar mode uses its TP1 activation distance. Disable the filter to compare baseline behavior.
- Dynamic sizing includes estimated execution costs within the existing risk budget. Fixed sizing retains its quantity cap.
- Break-even prices cover estimated round-trip costs when a break-even mode is enabled; the default mode now activates at TP1. Both directions round outward to chart ticks.
- Empty Webhook Market Symbol Override uses chart base + quote currency, avoiding BTC orders from an ETH chart. Configure an override for execution services using different identifiers. Verify perpetual support and quantity units.
- Replacement-stop alerts preserve actual fractional remaining quantity.

Estimated Fee Per Side (0.06%) and Estimated Slippage Per Side (2 ticks) must match Strategy Properties. Pine cannot read those Properties values. Estimates exclude funding, spread and actual fill variation. Entry checks use current ATR; exit distances use ATR at fill. A planned target passing the filter does not ensure a profitable trade, especially on early stops or reversal exits.

Defaults retained: all seven days, 24-hour allowed session, blocked intraday windows off, EOD liquidation off, New York midnight risk-day reset, 0.001 base-coin step, 1 base coin maximum/fixed size, 1x margin. Set step and size for the selected market. News filters and original FVG/Fibonacci/ORB logic remain. NY and London ORBs remain time-based signals; daily VWAP follows the chart anchor.

External dependency: access to traderjoeb/PropFirm_News_Dates/6 is required. A copy published under another profile requires updating the import path.

Validation: static coverage of all six entry paths; mathematical checks that cost-adjusted BTC/ETH break-even prices cover modeled fees/slippage and dynamic sizing stays within the modeled risk budget; git diff whitespace check. TradingView compilation, new backtests and broker webhook execution have not been performed. No improved return is claimed.

Current default candidate for BTCUSDT perpetual, 1-minute: minimum target/cost ratio 2.0, ADX 25, minimum FVG score 55, minimum Fib Action score 55, risk 0.15%, score-based risk scaling off, wick-based hard stops. These are recommended trial defaults, not a backtest-verified optimum. ATR targets, trailing settings and enabled trading days are retained. Existing TradingView strategy instances may retain previous input values: reset settings or add a fresh instance to use these defaults.

Break-even at TP1 is now enabled by default (Move SL to Break-Even = 1), with estimated costs included. This is a trial exit adjustment prompted by the BTC export, not a verified performance improvement. Reset existing TradingView inputs to apply the new default and recreate alerts after updating.
