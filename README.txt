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
