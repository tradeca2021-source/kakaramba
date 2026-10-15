# MNQ RBO v75 with EngineeringRobo entries

Use `MNQ_RBO_v75_EngineeringRobo.pine` as a complete replacement script in TradingView. It is based on the uploaded MNQ RBO v75 Tester, not the small EngineeringRobo demonstration strategy. The supplied news library import `traderjoeb/PropFirm_News_Dates/6` is still required. Library availability and native compilation cannot be verified locally.

## Entry behavior

AI POWER defaults to 2.5. EngineeringRobo's existing Supertrend (ATR length 10) confirmed upward direction change produces BUY; downward change produces SELL. Marker conditions match the isolated signal engine the user displayed on BTC. No claim is made that these reproduce the original proprietary indicator.

A signal submits a market order only while flat, within the inherited permitted timeframe/day/session/news windows, outside EOD, and without a daily kill switch. It also requires a positive ATR and point value and a valid stop on the correct side of the signal close. Blocked signals expire: a subsequent reversal is required. Open positions are managed by the original MNQ exits, rather than automatically reversing on EngineeringRobo signals. Market orders retain next-available-tick execution; labels mark decisions, not fills. Quantity constraints can prevent an otherwise valid signal from producing an order.

Revision r2 accepts seconds charts and minute charts up to Maximum entry timeframe, default 15 minutes. Tuesday remains disabled by default, and New York trading/news exclusions remain active. The BTC 15-minute example is now entry-timeframe eligible, subject to all remaining rules. Standard 1–5 minute MNQ charts remain the closest match for the inherited research/exits. Higher chart timeframes do not recreate missing intrabar detail. Matching signals on another symbol or timeframe is not expected.

The alternating tester sequence and dummy 80-tick stops are removed. Both original FVG setup-arming paths and all four FVG limit/rejection-limit execution paths are explicitly disabled, so FVGs cannot independently open positions. Their calculations remain where needed for exits, chart displays and compatibility. Legacy FVG entry/quality settings no longer control EngineeringRobo entries; Entry Execution is always market in this version. The old VWAP/ADX/FVG setup filters are not added as conditions to the new raw reversal signals.

## Risk and exits

Dynamic contract sizing, Max/Fixed Contracts, per-trade risk limits, point-value conversion, partials, break-even, original multi-target exits, bar-by-bar trailing, emergency stops, EOD liquidation and webhook wrappers are retained. Source strategy properties remain USD 100,000 initial capital, $0.54 per contract commission, two ticks slippage, original margin settings and bar magnifier enabled. These are inherited assumptions, not verified current broker charges.

New entries have fresh signal-bar metadata and stops. Available stop modes are 1: signal candle low/high, 2: latest confirmed micro swing, 3: signal-close ATR, and 5: entry-reference ATR. Default remains mode 3 with the existing session-adjusted ATR multiplier. Mode 5 uses the signal close as its pre-fill entry reference, as the source market-order path does; it is not recomputed from an unknown future fill. Stops round outward to instrument tick size. A missing or wrong-side stop skips the signal. FVG boundary modes 0 and 4 are unavailable because these entries do not have an FVG boundary.

EngineeringRobo entries have no FVG formation score or penetration. Base Risk Per Trade and existing per-trade cap apply without score scaling or FVG-combo multipliers. No score is fabricated and no stale FVG state is used. Strong Opposite FVG exits remain available: for an entry with no FVG score, they compare against the configured Minimum FVG Score multiplied by Strong Opposite FVG Strength Factor. Any Opposite FVG mode and Disabled mode retain their existing meanings.

The tester hardcoded its daily hard-stop, profit-kill and daily-kill flags to false. This integration restores their commented configured expressions so existing daily risk controls actually operate. This can materially reduce trade counts compared with the tester. The original manager's bar-close monitoring, modeled fill behavior, risk formula limitations and exposure to gaps remain; these edits do not establish exact realized-loss bounds.

## Webhooks and review

All entry orders go through the uploaded execution wrapper, and exit management uses the uploaded wrappers. JSON field structure and TradingView placeholders remain; `script_variant` changes from `tester` to `engineeringrobo`. Entry UUIDs use an `ER-` prefix and formation-specific metadata is cleared rather than recycled. No webhook or external message was sent during this work. Recreate TradingView alerts after replacing the source so old server-side script snapshots do not continue using tester entries.

18 source-expression entry-gate scenarios passed, including long/short signals, open positions, unconfirmed bars, session/EOD/daily blocks, invalid ATR/point value, missing stops and wrong-side stops. Preservation checks confirmed the inherited exit manager matches the uploaded source except for the documented strong-opposite-FVG baseline. Legacy entry isolation, tester removal and source delimiter checks also passed. These checks do not compile Pine or simulate TradingView execution. Native compilation, news library access, fills and performance require Strategy Tester validation.


## Direction switches

Under Inputs → EngineeringRobo Signals, Swap BUY/SELL signals defaults off. Turning it on converts the original BUY into a short-direction SELL and the original SELL into a long-direction BUY. Both displayed labels and order direction use the same mapping. Enable BUY trades and Enable SELL trades default on and independently permit long and short entries after mapping. Disabling a direction blocks its new entries without hiding raw labels or interrupting management of existing positions. These switches do not bypass flat-position, schedule, daily-risk, stop-validity or quantity rules; they do not force immediate position reversals.


## No-trade diagnosis on sub-minute charts

The original minute-only guard rejected all seconds charts even while raw BUY/SELL markers remained visible. Seconds charts are accepted; revision r2 also accepts minute charts up to the configured maximum, default 15. Tick, range and daily charts remain unsupported for entry. The separate legacy ORB calculations keep their short-timeframe guard. The default 22:00–01:00 New York blocked session still excludes signals around 23:20. To trade that window, explicitly edit Blocked Intra-Day Session or its enable switch; the code does not silently bypass it. Weekday, news, EOD and daily-risk checks remain in force.

The entry-status panel reports the current blocker, the last confirmed signal's result, total raw signals, submitted order calls, and open/closed trade counts. A submitted order is not proof of a fill: capital, margin, minimum instrument size and broker-emulator rules still apply. Trade counts can include partial exits and are not counts of whole-position round trips. Changing swaps or enabling directions cannot overcome a blocked schedule.


## Revision r2: configurable entry timeframe and visible counters

The chart title/short title identifies this revision as MNQ ER r2. Maximum entry timeframe (minutes) defaults to 15 and accepts values 1–60. This guard controls new EngineeringRobo entries separately from legacy ORB calculations. Schedule/day/news/risk filters are preserved.

The three additional status-line/Data Window values, in order, are Raw signal count, Submitted order count, and Last signal block code. Code 0 means no gate blocker was recorded; it does not guarantee a fill. Codes: 1 unsupported timeframe; 2 weekday disabled; 3 EOD; 4 blocked intraday/day-specific session; 5 news; 6 daily or consecutive-loss limit; 7 outside allowed session; 8 existing position; 9 invalid ATR/point value; 10 direction disabled; 11 invalid stop; 12 insufficient risk budget to size one whole contract. These codes describe the last raw signal, not necessarily the current bar. Counts describe the chart execution context and can differ from a separate Deep Backtesting range. If orders are submitted but no fills occur, inspect capital/margin and instrument quantities in Strategy Tester.

21 entry-gate and 9 configurable timeframe scenarios passed against extracted source expressions. The revised 15-minute default and explicit 30-minute opt-in were covered; native Strategy Tester execution remains unverified.


## Revision r3: expose the existing diagnostics

The supplied r2 screenshot confirmed that version was loaded, but its input values occupied the visible status line and the diagnostic outputs were not readable. Revision r3 hides input values from the status line/Data Window via input display settings while keeping all controls accessible in Settings → Inputs. No entry, sizing, session, exit or webhook behavior changes from r2. The three numeric diagnostics should be read with the crosshair on the most recent bar, or by their names in the Data Window: Raw signal count, Submitted order count, Last signal block code. Their values are still required to establish the remaining blocker; a chart screenshot with only signal labels cannot do that.

## Revision r4: direct order calls and per-signal blockers

The two active EngineeringRobo market-entry paths now call `strategy.entry` directly. The market branch of the original execution wrapper was inlined with the same entry IDs, direction, explicit quantity, comment builder, emergency-stop snapshot and webhook payload builder. This is an execution-path simplification, not proof that the wrapper caused the reported zero trades. Legacy limit/rejection entries remain disabled and exit management remains unchanged.

Green BUY ORDER and red SELL ORDER markers now mean the corresponding entry call executed. They do not prove that TradingView filled the order. Raw reversals that are blocked produce an orange reason at the top of that candle while Show entry status is enabled: TIMEFRAME, DAY, EOD, SESSION, NEWS, DAILY LIMIT, ALLOWED HOURS, POSITION OPEN, ATR / POINT VALUE, DIRECTION OFF, STOP, or ZERO QTY. This avoids requiring the status table or Data Window to identify an entry gate. Show BUY/SELL signals controls submitted-order markers; raw reversal totals remain in the diagnostic counts.

Do not treat an empty report as evidence of a fixed source defect without native execution evidence. If BUY ORDER/SELL ORDER markers appear with no trades, eligibility checks passed and an order was requested; inspect execution errors, capital, margin, instrument quantity restrictions and the backtest range. If orange markers appear, their stated rules are the blockers. A separate Deep Backtesting run can have different history from the visible chart.


## Revision r5: restore raw signal markers

Revision r4 replaced the raw AI BUY/SELL plots with submitted-order plots. This concealed the visible signals whenever no order was submitted. Revision r5 restores the original raw AI BUY/SELL markers near the signal engine, independent of trade eligibility. Separate small ORDER circles identify actual entry calls. Orange blocking-reason labels now use above-bar placement instead of the top edge of the pane. Entry, sizing, exit and webhook logic are unchanged from r4. Restoring marker visibility does not establish that the no-trade cause has been resolved.

## Revision r6: entry decisions inside signal labels

Raw AI BUY/SELL signals now use drawing labels containing the entry decision itself when Show entry status is enabled. Each includes its blocker or eligibility result, stop distance, calculated quantity, equity, and dollar risk budget. Orange labels mean the signal was blocked; a directional green/red label means no listed entry gate blocked it, not a guaranteed fill. Show BUY/SELL signals still controls these labels. Small ORDER circles separately indicate actual entry calls. Labels are subject to TradingView's drawing retention limit, so very old raw markers may be discarded. No source, session, or risk gate is bypassed to fabricate trades.

A Fixed EngineeringRobo contracts input defaults to one and is used only when Use Dynamic Sizing is set to 0. Max/Fixed Contracts still caps it. Dynamic sizing remains on by default and is unchanged: if the configured risk budget cannot afford one whole contract at the chosen stop, quantity remains zero. Fixed mode is an explicit allocation decision and can exceed the percentage risk budget; original emergency stops and exit management remain, without guaranteeing gap-safe loss bounds. Source-level checks covered six quantity cases, ensuring previews and both active order paths use the same fixed quantity. Pine compilation and fills remain unverified.
