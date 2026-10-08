RBO v88: actionable trade / wait / skip decisions

Top-right decision panel shows LONG/SHORT LIMIT SUBMITTED (awaiting an actual fill), LONG/SHORT OPEN, WAIT with no entry order, SKIP NOW with the engine reason, or canceled/waiting for another pair. It displays local confirmed structure and pending-change progress, exact frozen order entry/target/stop/quantity when active, and estimated net economics. Candidate-only prices are clearly marked as informational; they do not authorize an entry or indicate that an order was accepted. The panel describes the latest/current engine state, not every candle visible when scrolling history.

Default take rules: a long requires bullish confirmed structure, a confirmed upward Fib, a resting front-run50% limit, no strong resistance obstructing its61.8% directional target, positive estimated target after costs, permitted time/risk gates and valid quantity/stop. A short uses the corresponding bearish rules with strong support checked. Source inputs can disable optional trend/SR/quality gates; read settings before interpreting decisions.

Trend UP/DOWN markers reflect local chart-timeframe swing structure, not a guarantee about the whole multi-week trend. A rising chart can still contain locally confirmed bearish changes. Those markers are not entry signals. Raw FIB L/S triangles are candidates; BUY/SELL LIMIT labels are submission attempts; native TradingView order markers show actual fills.

WAIT/SKIP NOW/CANCELED labels mark closed-bar changes in the engine's reason and provide full reason plus candidate/canceled-order prices on hover. They do not annotate every rejected pair or every bar; the latest80 decision labels are retained. SKIP NOW is a current rejection, not a promise that a temporarily blocked pair will never retry. Cancel labels reference the canceled order side/prices, even if the latest candidate has changed. Both panel and decision labels can be hidden in Chart & Dashboard.

Trading logic is unchanged from v87. Source comparison and whitespace checks verify the entry-management function remains identical. Native TradingView compilation, fills and profitability are not newly verified. Previous notes follow:

RBO v87: optional deviation-confirmed Fib anchors from the supplied Fib Swing v4

Useful ideas in the uploaded script: filter smaller swing legs by reversal size, separate provisional extreme tracking from locked anchors, retain distinct times/bars for high/low, and make Fib boundaries visible. Its orders are disabled; its internal up/down tracking direction is not sufficient evidence of market trend. Original wick-based checks can create provisional intrabar changes and do not establish an instant/no-delay macro swing. Its observational61.8% pullback trade level also differs from our50% entry and directional61.8% profit target.

v87 adds Deviation Confirmed Pair to Impulse Anchors, with0.25% reversal as an UNOPTIMIZED starting input. Confirmed Swing Pair remains default. The tracker starts unknown instead of assuming bullish. It requires CLOSED-price percentage reversal, locks chronological distinct-bar high/low pairs and exposes only completed pairs as order candidates. Running extremes never move an existing candidate. Pair age starts at actual deviation confirmation, not endpoint bar plus pivot delay. Separate trend and strong-S/R gates remain active; tracking-leg direction never overrides them. Existing order snapshots/50% entry/61.8% target are retained. Optional anchor high/low plots and dashboard source/threshold make the selected method visible.

Important tradeoff: deviation filters noise but introduces price-reversal delay. For an up leg ending at H, a d-fraction reversal confirms at or below H*(1-d). To confirm while still above midpoint, impulse range R must exceed2*d*H (before front-running ticks). At2.5%, that requires a range larger than5% of H. Smaller swings can confirm after50% was already crossed. At high85,000 and low83,500,2.5% confirmation occurs around82,875, below the50% entry84,250. v87 retains resting-limit/retry logic and does not backfill missed touches. Down-leg timing has the symmetric limitation. Threshold choice needs venue-specific out-of-sample testing, not a claim that0.25% is best.

Local checks cover unknown initialization, close-only confirmations, frozen completed anchors, chronological pair directions, same-bar ambiguity rejection, confirmation-based expiry and unchanged default pivot behavior/entry geometry. Native Pine compilation and trading performance remain unverified. Deviation mode can still replace a pair on a subsequent significant reversal; a multi-candidate queue is not implemented here. Previous notes follow:

RBO v86: avoid strong support/resistance in the Fib target path

Avoid Strong Opposing S/R Before Target defaults ON. Strong resistance obstructs long entries, and strong support obstructs shorts, when the zone overlaps entry-to-target or lies within the configured clearance beyond target. This is a target-path check, not a requirement to enter only after a support bounce. The user-confirmed trend gate remains ON and Fib50%/61.8% geometry stays fixed.

Zones use independent5-left/5-right confirmed pivots. A zone becomes strong after2 separately confirmed pivot touches at least5 bars apart. Only pivots of the same current role merge, within its original frozen half-width (0.25 ATR at creation, minimum1tick). Centers/widths do not move with later ATR. At most20 zones are retained; the oldest-created is evicted when capacity is reached. Zones expire after500 bars without a counted confirmed touch. These configurable defaults are implementation choices, not proven optima.

Two consecutive CLOSED candles beyond the full zone plus2ticks confirm a breakout and flip resistance into support or support into resistance, preserving its historical strength. Wick-only penetrations and a single close do not clear an opposing obstacle. Old-zone breakout processing precedes insertion of newly confirmed pivots, with no backdated entries. The target clearance is0.1 current ATR. Unfilled limits are canceled at calculation time if a newly strong opposing zone obstructs the frozen target path; already-open trades keep their brackets. A fill earlier in the bar cannot be retrospectively canceled by closing-bar confirmation.

Red/green lines show the nearest strong resistance/support center relative to current close. The blocking calculation uses full zone edges relative to the planned entry/target, so its obstacle can differ from the center line shown. An orange obstacle-edge line shows the selected blocker even when its center is absent from the nearest current-price plots. Dashboard reports nearest blocking edge and counted strength; simultaneous candidate flags include S/R. No detected strong obstacle means none among retained confirmed zones, not absence of all market resistance or support. Disabling the gate removes its effect while preserving informational readings.

Local checks cover zone clustering/spacing/cap/expiry, confirmed breakout role flips, long/short target-path obstruction and pending/open integration. Native TradingView compilation and comparative performance remain unverified; additional gating can reduce fills. Previous notes follow:

RBO v85: confirmed structural trend before the next Fib trade

The user now requests trend identification and confirmation of trend changes before entries. This supersedes the earlier preference to allow both trend and countertrend trades. Require Confirmed Trend Before Fib Entries defaults ON; switch it off to restore the earlier direction eligibility.

Definition: independent chart-timeframe 5-left/5-right confirmed swing pivots, with a2-tick break buffer. A close above the previously known swing high starts bullish confirmation; a close below the previously known swing low starts bearish confirmation. Initial direction requires both swing reference prices to exist and form a valid high/low range. Once bullish, a break of the known low is sufficient to start bearish confirmation; once bearish, a break of the known high is sufficient to start bullish confirmation, even when independently updated bounds temporarily invert. Two consecutive closes beyond the same frozen break level confirm the direction. A wick alone does not start confirmation. A failed subsequent close clears the possible change and retains the prior confirmed direction. The threshold is frozen during confirmation and current-bar pivots update references only after break evaluation. Initial state is UNKNOWN; it does not assume an uptrend from the screenshot. Defaults are explicit implementation choices, not optimized parameters.

Entry behavior: only long Fibs in confirmed bullish structure, or short Fibs in confirmed bearish structure. UNKNOWN or a change awaiting confirmation blocks all new entries. Trend mismatch does not consume an unsubmitted candidate before its existing expiry/replacement. Unfilled limits are canceled at calculation time when the trend becomes unconfirmed or opposed. Already-open trades continue with their frozen Fib stop/target. A limit may fill intrabar before the closing calculation detects a change; close-based confirmation cannot retrospectively prevent that fill.

Dashboard shows confirmed direction, pending direction, progress toward required consecutive closes, frozen confirmation price and gate ON/OFF. TREND UP/DOWN markers appear on the actual confirmation bar, without backdating to pivot bars. Higher timeframes, VWAP,volume or reaction are not mandatory parts of this definition. Fib50% entry/directional61.8% target, cost gates and quantity guards remain in place. This does not fix marginal fee economics or prove improved win rate/profit factor. Local lifecycle/source checks were run; native TradingView compilation/fills remain unverified.

Previous notes follow (statements about unchanged trading rules refer to previous versions):

Additional screenshot evidence: the user confirmed BTCUSDT perpetual, 1-minute. A subsequent screenshot shows a native +0.276 entry and -0.276 Blind Fib PT exit; the futures hypothesis is not established for this run, and the engine demonstrably filled at least one position. Its displayed entry72,668.5 and target72,758 imply89.5 gross price-distance reward. At0.06% per side, modeled entry/exit fees consume87.2559 distance per BTC, leaving about0.61937 USDT on0.276 BTC before spread, slippage or funding. Exact realized PnL needs the trade report. A PT exit is not evidence of useful net reward/risk. v84 also increases estimated net-RR precision and exposes gross/cost/net target distances so two-decimal rounding does not conceal tiny positive net reward. No new filter threshold or profit improvement is claimed.

RBO v84: enforce chart minimum quantity and identify the actual instrument

The supplied v83 screenshot shows limit-submission labels but an empty strategy report. Its symbol header is cropped; prices around 30,000 and ETH/B-ADJ session labels suggest futures, but the exact symbol is unconfirmed. Those labels are order attempts, not evidence of accepted or filled orders. Lack of fills can also result from untouched/canceled/expired limits.

Source review found a concrete sizing mismatch: v83 floors solely to the 0.001 base-coin step and does not consult syminfo.mincontract. A chart requiring whole contracts can therefore receive sub-contract attempts. Example only: at price30,000 and pointvalue20, 100,000 equity and 100% margin allow about0.166 contracts; they do not afford a whole contract. This does not establish that the screenshot's instrument is NQ or that fractional sizing is its only blocker.

v84 reads the chart minimum quantity, normalizes the configured step upward to a multiple of it, and floors the risk/capital-capped size to that effective step. Orders below one effective step are blocked before submission. Missing/nonpositive symbol minima fall back to the configured step. Limits show their actual quantity and the dashboard displays exact tickerid, symbol type, point value, chart minimum, effective step and maximum size after the existing 1x equity and quantity caps. The counter now says Order attempts, since a strategy.entry call does not confirm acceptance.

BTCUSDT perpetual remains the intended market. Confirm the actual chart symbol and use the correct BTCUSDT perpetual chart for BTC testing. This sizing guard does not convert the strategy to a futures-specific strategy, change leverage/capital, or change its percentage-based fee model. TradingView chart minima may differ from external broker minimum notional/lot rules. Existing minimum/fixed size, cost and risk settings may need correction on another market.

Local checks cover fractional BTC sizing, whole-contract affordability/risk limits, step normalization and unchanged Fib geometry/brackets. TradingView compilation and actual fills remain unverified. Previous notes follow:

RBO v83: signal context from three independent agent reviews

New informational readings: current confirmed-pair range / current ATR, planned front-run 50% entry alignment relative to current VWAP, and current bar volume divided by the previous 20-bar volume SMA. Warm-up or unavailable values display n/a. RVOL is exchange volume, not order flow. These readings change over time and are not frozen at setup confirmation. They do not introduce new entry filters or establish better profitability. The existing optional VWAP entry gate still checks current close; the new VWAP reading describes planned-entry location separately.

The dashboard also shows simultaneous selected midpoint, net-target-cost, optional cost-filter and safety blockers. This avoids the first midpoint reason hiding a fee rejection. "Clear" applies only to these selected checks; expiry, valid stop/size, optional VWAP and minimum net-RR can still block submission. Fixed two diagnostic defects: near-news pre-liquidation windows now count as safety-blocked pairs, and unsupported chart timeframes show Offline even if time restrictions are disabled.

Review findings and priorities:
- Every new opposite pivot replaces the sole current candidate. A waiting pair can disappear before its retry age expires. A bounded collection of independently tracked pairs is the next structural improvement to consider, with explicit origin invalidation, expiry and selection rules; v83 does not change that policy.
- Raw FIB L/S triangles identify confirmed candidates. BUY/SELL LIMIT labels indicate submissions, and native TradingView order markers identify actual fills. Additional mandatory indicators would further reduce trades.
- A positive modeled target can still have a high estimated break-even win rate. No new optimum ATR, VWAP, volume or net-RR threshold is established.
- Webhook fill-triggered limits and the broker emergency stop differ from the resting Fib bracket simulated by TradingView; live execution requires separate validation.

Local validation checks verify unchanged execution engine/defaults, corrected status/safety conditions, and indicator/blocker arithmetic. Native TradingView compilation, market replay and performance improvement remain unverified. Use separate development/evaluation periods to compare fill rate, completed parent positions, net profit factor, net expectancy, drawdown and fees before enabling new filters.

Previous version notes follow:

RBO v82: retry a pair whose midpoint was crossed at confirmation

The user confirmed the current chart status is "Skipped: midpoint already crossed". The prior engine marked that pair consumed before any order was submitted. That prevented a later eligible entry on the same pair even after price returned to the resting-limit side.

v82 keeps a crossed, unsubmitted CURRENT pair eligible until it expires or is replaced by a newer confirmed pair. A long limit can submit when close returns to or above the front-run 50% entry; a short limit can submit when close returns to or below it. Until then, status reads "Waiting: price beyond 50%; retry until expiry". Submission is evaluated at bar close and the limit fills only on a later available tick. This does not backdate an entry, chase price with a market order, or guarantee the pair gets a second opportunity. Expired/invalid pairs and already submitted, canceled or completed series remain consumed.

The 50% entry, directional 61.8% target, confirmed pivot anchors, fee eligibility and safety rules are unchanged. v81's equality correction and whole-chart diagnostic counters are included. The independent fee gate can still reject smaller swings; a crossed status alone does not show whether those setups pass the other gates. Local lifecycle checks cover both directions, reclaim/retry, duplicate prevention, expiry, cancellation and fee rejection. TradingView compilation and chart fills have not been verified locally.

Previous investigation and implementation notes follow; descriptions of consuming crossed pairs apply to v81 and earlier only:

RBO v81: investigate missing Fibonacci trades

Two source-level causes can suppress entries on BTCUSDT perpetual 1-minute:
1. The v80 positive-net-target gate is ON. With 0.06% fees per side and the requested 50% entry / directional 61.8% target, gross reward is only 11.8% of the anchor range, less front-running ticks. At entry 85,000 and tick 0.1, an impulse around 871 points is required just to cover modeled fees/slippage. Small local 3/3 pivot pairs fail this gate. Raising size does not improve these per-unit economics.
2. Pivots become known after three right-side bars. If price is already strictly beyond the midpoint at confirmation, the script consumes that pair rather than backdating a limit or chasing the price. v81 fixes an equality boundary: price exactly at the entry may now submit a limit for the next available tick. It does not simulate an earlier fill.

No current TradingView chart/export was available to prove which cause dominates the user's run. A public market-data request was blocked by the environment network proxy, so no market replay or performance claim was made. A native Pine compiler is unavailable locally.

The v81 dashboard adds whole-chart pair, submitted-limit and filled-position counts, plus independent counts of pairs already crossed, blocked by the positive-net guard, blocked by safety rules, or observed while busy AT CONFIRMATION. These counts overlap and are not additive. Pairs blocked temporarily can later retry; the snapshot counts do not imply permanent rejection. Limits sent with zero fills means entries were submitted but not filled in the selected chart history. Filled means closed positions plus the currently open position for this one-position engine. Zero submitted limits means eligibility/state needs investigation, not that TradingView ignored a plotted setup.

It also displays the current pair's price range, an approximate fee break-even range, the saved cost-gate settings and pivot confirmation bars. The approximate range uses entry-price round-trip costs; the actual eligibility gate uses entry plus target-price fees and tick-rounded levels. Use the complete v81 script in a fresh TradingView instance and read these dashboard rows to identify the blocker across the whole chart. No economic guard, schedule or risk safeguard has been disabled and the confirmed-anchor 50% / 61.8% method is retained. The equality correction and diagnostics were checked locally using deterministic long/short scenarios; these checks do not establish real chart fills or profitability.

Previous implementation notes follow (v79/v80 references describe those revisions):

RBO v80: cost-aware target eligibility and realized exit diagnostics
Investigation update: no current v79 export was supplied, so actual stop-hit causes and win rate cannot be established locally. The source does permit fee-negative target trades when its cost gate is off. At BTC 85,000, a 600-point impulse gives about 70 points of target reward versus about 102 points per BTC of modeled round-trip costs. The requested 50/61.8 geometry is unchanged.

v80 adds an independent Require Target to Cover Estimated Costs guard, ON by default. It calculates expected target proceeds after entry+target-price fees and two-sided estimated slippage. This rejects a target modeled to lose even if reached, while leaving the stronger target/cost >= 2 filter optional. Minimum Net Reward / Net Risk defaults 0 (off); there is no backtest evidence for an optimal floor. Diagnostic break-even win rate assumes every position exits at the modeled target or stop with similar sizing; it is not a forecast, an observed win rate, or an assurance of profitability.

The dashboard now shows estimated net reward/risk, required break-even win rate, actual TP exit count, how many TP exits lost in net terms, stop exit count and the last completed position's realized net PnL. Counts use new closed-position net-profit deltas for this one-position, full-exit engine. These separate fee losses from stop failures and are historical totals for the loaded chart. Match estimated fees/slippage to Strategy Properties; actual gaps, funding, spread and webhook fills can still differ.

Use a fresh instance or reset inputs to activate the new guard. No current v80 TradingView compile/backtest was run locally. Local source/mathematical checks passed; no profit improvement is claimed. Upload the current BTC trade export with Properties and Trades sheets to diagnose anchor quality, stop distances and execution behavior from actual outcomes.

BTC_RBO_v74_Fib.pine retains its filename. Paste the complete file into a new TradingView Pine Editor script and add a fresh instance or reset saved inputs. The strategy title is v80. Existing instances can retain old cost-filter values.

Confirmed high/low pairs still use chart pivots with 3 bars on each side by default. Blind entry = directional 50%, front-run 2 ticks. Full-position profit target = directional 61.8%, front-run 2 ticks. Optional VWAP is off. Stop defaults to entry +/- 1.5 ATR; origin-stop option retained. Levels/size freeze once a limit and its bracket are submitted. No FVG, reaction, ADX or HTF trend gate. One pending/open series is managed at a time.

Why v78 could show no signals: markers and Fib plots only appeared after order submission. Its optional fee filter defaulted on and required a target distance twice estimated round-trip costs; for BTC 85,000 with tick 0.1, the local impulse needed roughly 1,739 USDT range. A temporarily blocked pair was also marked used before submission.

v79 changes:
- Confirmed-pair FIB L/FIB S markers and candidate entry/target lines appear even when trading gates block an order. These are SETUPS, not order fills or guaranteed trades. Frozen order lines take precedence while pending/open.
- The dashboard shows the last entry/cancellation reason: crossed level, expiry, ATR warm-up, session/day/news or daily lockout, optional VWAP, optional cost filter, size step or stop validity.
- Temporary blockers can retry until the candidate expires (default 30 bars after endpoint confirmation). Crossed/invalid/expired pairs and submitted, canceled or completed orders stay consumed; no repeated trading of the same unchanged pair.
- Filter Entries by Trading Costs defaults OFF to follow the requested blind-entry method. TradingView commission remains 0.06% per side, modeled slippage remains 2 ticks per side and estimated costs remain included in risk sizing. Small targets can therefore produce trades with negative net economics; this change is not a profitability improvement. Re-enable the filter if desired.

Risk defaults: 0.15% trade risk, maximum/fixed base-coin size 1, quantity step 0.001, 1x equity cap, daily/news/session and consecutive-loss safeguards retained. Set step/fees to your exchange and use a supported 1-15 minute chart. Existing cost-filter, schedule and other saved settings survive source updates until reset.

News library traderjoeb/PropFirm_News_Dates/6 remains required. Webhooks remain order-fill based and do not pre-place native exchange limits/brackets; broker ESL is a separate failsafe.

Static checks and arithmetic/lifecycle scenarios passed locally. TradingView compilation and actual chart fills remain unverified. Replace the entire editor contents with the new file; no profitability gain is claimed.
